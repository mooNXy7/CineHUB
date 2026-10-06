#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 7 multi-source EPG engine.

The engine is additive: it reads the normalized/resolved channel manifests,
fetches configured XMLTV sources, normalizes channel/program data, merges
sources by priority, and publishes a compact rolling schedule for clients.

It never modifies WEB/Mobile/TV application data.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "CineHUB_Data/sources/registry.json"
CHANNELS_PATH = ROOT / "CineHUB_Data/resolved/channels.json"
OUTPUT_DIR = ROOT / "CineHUB_Data/epg"
OUTPUT_PATH = OUTPUT_DIR / "schedule.index.json"
STATUS_PATH = ROOT / "CineHUB_Data/status/epg-status.json"

TIMEOUT = int(os.environ.get("CINEHUB_EPG_TIMEOUT", "30"))
MAX_BYTES = int(os.environ.get("CINEHUB_EPG_MAX_BYTES", str(80 * 1024 * 1024)))
RETRIES = 2
HORIZON_HOURS = int(os.environ.get("CINEHUB_EPG_HORIZON_HOURS", "48"))

def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c))

def canonical(value: str) -> str:
    value = strip_accents(value).casefold()
    value = re.sub(r"\\[[^]]*\\]|\\([^)]*\\)", " ", value)
    value = re.sub(r"\\b(?:hd|fhd|uhd|sd|4k|8k)\\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()

def stable_channel_id(value: str) -> str:
    return "channel-" + hashlib.sha256(canonical(value).encode()).hexdigest()[:16]

def parse_dt(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    m = re.match(r"^(\\d{14})(?:\\s*([+-]\\d{4}|Z))?$", value)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
        tz = m.group(2)
        if tz == "Z":
            return dt.replace(tzinfo=timezone.utc)
        if tz:
            sign = 1 if tz[0] == "+" else -1
            minutes = int(tz[1:3]) * 60 + int(tz[3:5])
            return dt.replace(tzinfo=timezone(sign * timedelta(minutes=minutes))).astimezone(timezone.utc)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def text_of(parent: ET.Element, tag: str) -> str:
    node = parent.find(tag)
    return " ".join("".join(node.itertext()).split()) if node is not None else ""

def fetch_xml(url: str) -> bytes:
    last = None
    for attempt in range(RETRIES + 1):
        try:
            req = Request(url, headers={
                "User-Agent": "CineHUB-Data-Engine/7.0",
                "Accept": "application/xml,text/xml,*/*",
                "Accept-Encoding": "identity",
            })
            with urlopen(req, timeout=TIMEOUT) as response:
                chunks, total = [], 0
                while True:
                    chunk = response.read(min(1024 * 1024, MAX_BYTES - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError(f"EPG exceeds {MAX_BYTES} bytes")
                    chunks.append(chunk)
                body = b"".join(chunks)
                if not body.strip():
                    raise ValueError("empty EPG response")
                return body
        except HTTPError as exc:
            last = exc
            if exc.code in {401, 403, 404}:
                break
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            last = exc
        if attempt < RETRIES:
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last) if last else "unknown EPG fetch error")

def load(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def channel_map() -> tuple[dict[str, str], dict[str, dict]]:
    data = load(CHANNELS_PATH, {"channels": []})
    by_key: dict[str, str] = {}
    meta: dict[str, dict] = {}
    for ch in data.get("channels", []):
        cid = ch.get("id")
        if not cid:
            continue
        meta[cid] = {"id": cid, "name": ch.get("name"), "aliases": ch.get("aliases", [])}
        for value in [ch.get("name"), *ch.get("aliases", [])]:
            if value:
                by_key[canonical(value)] = cid
        for src in ch.get("sources", []):
            tvgid = src.get("tvgId")
            if tvgid:
                by_key[str(tvgid).casefold()] = cid
    return by_key, meta

def parse_source(body: bytes, source_id: str, channel_lookup: dict[str, str], now: datetime, end: datetime):
    schedules: dict[str, list[dict]] = {}
    seen_channels = 0
    programs = 0
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"invalid XMLTV: {exc}") from exc

    epg_ids: dict[str, str] = {}
    for node in root.findall("channel"):
        eid = node.get("id", "").strip()
        names = [" ".join(x.itertext()).strip() for x in node.findall("display-name") if "".join(x.itertext()).strip()]
        target = None
        if eid:
            target = channel_lookup.get(eid.casefold())
        if not target:
            for name in names:
                target = channel_lookup.get(canonical(name))
                if target:
                    break
        if target:
            epg_ids[eid] = target
            seen_channels += 1

    for node in root.findall("programme"):
        eid = node.get("channel", "").strip()
        target = epg_ids.get(eid)
        if not target:
            target = channel_lookup.get(eid.casefold())
        if not target:
            continue
        start = parse_dt(node.get("start", ""))
        stop = parse_dt(node.get("stop", ""))
        if not start or not stop or stop <= start or stop < now or start > end:
            continue
        title = text_of(node, "title")
        if not title:
            continue
        item = {
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": stop.isoformat().replace("+00:00", "Z"),
            "title": title,
            "subtitle": text_of(node, "sub-title") or None,
            "description": text_of(node, "desc") or None,
            "category": text_of(node, "category") or None,
            "sourceId": source_id,
        }
        schedules.setdefault(target, []).append(item)
        programs += 1
    return schedules, {"channelsMatched": seen_channels, "programsMatched": programs}

def merge_schedules(source_results: list[tuple[dict, dict]], meta: dict) -> dict:
    merged: dict[str, dict[str, dict]] = {}
    for schedules, source_meta in source_results:
        priority = int(source_meta.get("priority", 9999))
        for cid, items in schedules.items():
            bucket = merged.setdefault(cid, {})
            for item in items:
                key = (item["start"], item["end"], canonical(item["title"]))
                current = bucket.get(key)
                if current is None or priority < current[0]:
                    bucket[key] = (priority, item)
    out = {}
    for cid, bucket in merged.items():
        items = [v[1] for v in bucket.values()]
        items.sort(key=lambda x: (x["start"], x["end"], x["title"].casefold()))
        for item in items:
            item.pop("sourceId", None)
        out[cid] = items
    return out

def run() -> int:
    registry = load(REGISTRY_PATH, {})
    sources = [s for s in registry.get("epgSources", []) if s.get("enabled") and s.get("url")]
    lookup, meta = channel_map()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=HORIZON_HOURS)
    results = []
    failures = []

    for source in sorted(sources, key=lambda x: int(x.get("priority", 9999))):
        started = time.perf_counter()
        try:
            body = fetch_xml(source["url"])
            schedules, stats = parse_source(body, source["id"], lookup, now, horizon)
            results.append((schedules, source))
            results[-1][1]["latencyMs"] = round((time.perf_counter() - started) * 1000, 2)
            results[-1][1]["bytes"] = len(body)
            results[-1][1]["status"] = "healthy"
            results[-1][1]["error"] = None
            results[-1][1]["stats"] = stats
        except Exception as exc:
            failures.append({"id": source.get("id"), "error": str(exc)[:500]})

    merged = merge_schedules(results, meta)
    channels = []
    for cid, info in meta.items():
        channels.append({
            "id": cid,
            "name": info.get("name"),
            "programs": merged.get(cid, []),
        })

    channels.sort(key=lambda x: (str(x.get("name") or "").casefold(), x["id"]))
    matched = sum(bool(x["programs"]) for x in channels)
    total_programs = sum(len(x["programs"]) for x in channels)

    output = {
        "schemaVersion": "1.0.0",
        "generatedBy": "CineHUB Data Engine Phase 7",
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "window": {
            "start": now.isoformat().replace("+00:00", "Z"),
            "end": horizon.isoformat().replace("+00:00", "Z"),
            "hours": HORIZON_HOURS,
        },
        "policy": {
            "strategy": "channel-id-then-canonical-name",
            "sourceStrategy": "priority-with-gap-fill",
            "expiredProgramsDiscarded": True,
            "clientProcessesXmltv": False,
        },
        "stats": {
            "sourcesConfigured": len(sources),
            "sourcesHealthy": len(results),
            "sourcesFailed": len(failures),
            "channelsKnown": len(channels),
            "channelsWithPrograms": matched,
            "channelsWithoutPrograms": len(channels) - matched,
            "programs": total_programs,
        },
        "channels": channels,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    status = {
        "schemaVersion": "1.0.0",
        "generatedAt": output["generatedAt"],
        "status": "healthy" if results and not failures else ("degraded" if results else "offline"),
        "sources": [{"id": s["id"], "priority": s.get("priority"), "status": s.get("status"),
                     "latencyMs": s.get("latencyMs"), "bytes": s.get("bytes"),
                     "stats": s.get("stats"), "error": s.get("error")} for _, s in results] + failures,
        "stats": output["stats"],
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status["stats"], ensure_ascii=False, indent=2))
    return 0 if results or not sources else 1

if __name__ == "__main__":
    raise SystemExit(run())
