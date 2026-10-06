#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 7 multi-source EPG engine.

Downloads configured XMLTV feeds with bounded retries, conditional HTTP caching,
channel-ID/name normalization, priority-based merge and gap filling. The
generated rolling schedule is platform-neutral and additive: existing
WEB/Mobile/TV data paths are not replaced.
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
CACHE_DIR = ROOT / "CineHUB_Data/.cache/epg"
OUTPUT_PATH = OUTPUT_DIR / "schedule.index.json"
STATUS_PATH = ROOT / "CineHUB_Data/status/epg-status.json"

TIMEOUT = int(os.environ.get("CINEHUB_EPG_TIMEOUT", "30"))
MAX_BYTES = int(os.environ.get("CINEHUB_EPG_MAX_BYTES", str(80 * 1024 * 1024)))
RETRIES = 2
HORIZON_HOURS = int(os.environ.get("CINEHUB_EPG_HORIZON_HOURS", "48"))
CACHE_TTL_HOURS = int(os.environ.get("CINEHUB_EPG_CACHE_TTL_HOURS", "12"))
MAX_FAILURES_FOR_OFFLINE = 3
MAX_FAILURES_FOR_DEGRADED = 2


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def canonical(value: str) -> str:
    value = strip_accents(value).casefold()
    value = re.sub(r"\[[^]]*\]|\([^)]*\)", " ", value)
    value = re.sub(r"\b(?:hd|fhd|uhd|sd|4k|8k)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def stable_channel_id(value: str) -> str:
    return "channel-" + hashlib.sha256(canonical(value).encode()).hexdigest()[:16]


def parse_dt(value: str) -> datetime | None:
    value = (value or "").strip()
    m = re.match(r"^(\d{14})(?:\s*([+-]\d{4}|Z))?$", value)
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


def text_of(node: ET.Element, wanted: str) -> str:
    for child in list(node):
        if local_name(child.tag) == wanted:
            return " ".join("".join(child.itertext()).split())
    return ""


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(failures: int) -> str:
    if failures >= MAX_FAILURES_FOR_OFFLINE:
        return "offline"
    if failures >= MAX_FAILURES_FOR_DEGRADED:
        return "degraded"
    return "unknown"


def cache_path(source_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id)
    return CACHE_DIR / f"{safe}.json"


def channel_signature(meta: dict) -> str:
    raw = "|".join(
        f"{cid}:{meta[cid].get('name','')}:{','.join(sorted(meta[cid].get('aliases', [])))}"
        for cid in sorted(meta)
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def channel_map() -> tuple[dict[str, str], dict[str, dict]]:
    data = load(CHANNELS_PATH, {"channels": []})
    by_key: dict[str, str] = {}
    meta: dict[str, dict] = {}
    for ch in data.get("channels", []):
        cid = ch.get("id")
        if not cid:
            continue
        meta[cid] = {"id": cid, "name": ch.get("name"), "aliases": ch.get("aliases", [])}
        values = [ch.get("name"), *ch.get("aliases", [])]
        for value in values:
            if value:
                by_key[canonical(value)] = cid
        for src in ch.get("sources", []):
            tvgid = src.get("tvgId")
            if tvgid:
                by_key[str(tvgid).casefold()] = cid
    return by_key, meta


def parse_source(body: bytes, source_id: str, lookup: dict[str, str], now: datetime, end: datetime):
    root = ET.fromstring(body)
    schedules: dict[str, list[dict]] = {}
    epg_ids: dict[str, str] = {}
    matched_channels = 0
    programs = 0

    for node in root.iter():
        if local_name(node.tag) != "channel":
            continue
        eid = (node.get("id") or "").strip()
        names = [
            " ".join("".join(x.itertext()).split())
            for x in list(node)
            if local_name(x.tag) == "display-name" and "".join(x.itertext()).strip()
        ]
        target = lookup.get(eid.casefold()) if eid else None
        if not target:
            for name in names:
                target = lookup.get(canonical(name))
                if target:
                    break
        if target:
            epg_ids[eid] = target
            matched_channels += 1

    for node in root.iter():
        if local_name(node.tag) != "programme":
            continue
        eid = (node.get("channel") or "").strip()
        target = epg_ids.get(eid) or lookup.get(eid.casefold())
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

    for cid in schedules:
        schedules[cid].sort(key=lambda x: (x["start"], x["end"], x["title"].casefold()))
    return schedules, {"channelsMatched": matched_channels, "programsMatched": programs}


def filter_window(schedules: dict, now: datetime, end: datetime) -> dict:
    out = {}
    start_iso = now.isoformat().replace("+00:00", "Z")
    end_iso = end.isoformat().replace("+00:00", "Z")
    for cid, items in schedules.items():
        kept = [x for x in items if x["end"] >= start_iso and x["start"] <= end_iso]
        if kept:
            out[cid] = kept
    return out


def load_cache(source: dict, signature: str, now: datetime, end: datetime):
    path = cache_path(source["id"])
    cached = load(path, None)
    if not isinstance(cached, dict):
        return None
    if cached.get("channelSignature") != signature:
        return None
    try:
        generated = datetime.fromisoformat(cached["generatedAt"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return None
    if now - generated > timedelta(hours=CACHE_TTL_HOURS):
        return None
    return {
        "schedules": filter_window(cached.get("schedules", {}), now, end),
        "etag": cached.get("etag"),
        "lastModified": cached.get("lastModified"),
        "generatedAt": cached.get("generatedAt"),
    }


def save_cache(source: dict, signature: str, schedules: dict, response_headers: dict) -> None:
    save(cache_path(source["id"]), {
        "schemaVersion": 1,
        "sourceId": source["id"],
        "channelSignature": signature,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "etag": response_headers.get("etag"),
        "lastModified": response_headers.get("last-modified"),
        "schedules": schedules,
    })


def fetch_xml(source: dict, cached: dict | None):
    last = None
    headers = {
        "User-Agent": "CineHUB-Data-Engine/7.0",
        "Accept": "application/xml,text/xml,*/*",
        "Accept-Encoding": "identity",
    }
    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    elif cached and cached.get("lastModified"):
        headers["If-Modified-Since"] = cached["lastModified"]

    for attempt in range(RETRIES + 1):
        try:
            req = Request(source["url"], headers=headers)
            with urlopen(req, timeout=TIMEOUT) as response:
                status = int(response.status)
                if status == 304:
                    return None, status, dict(response.headers.items())
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
                return body, status, dict(response.headers.items())
        except HTTPError as exc:
            if exc.code == 304:
                return None, 304, dict(exc.headers.items()) if exc.headers else {}
            last = exc
            if exc.code in {401, 403, 404}:
                break
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            last = exc
        if attempt < RETRIES:
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last) if last else "unknown EPG fetch error")


def merge_schedules(source_results: list[tuple[dict, dict]]) -> dict:
    merged: dict[str, dict[tuple, tuple[int, dict]]] = {}
    for schedules, source in source_results:
        priority = int(source.get("priority", 9999))
        for cid, items in schedules.items():
            bucket = merged.setdefault(cid, {})
            for item in items:
                key = (item["start"], item["end"], canonical(item["title"]))
                current = bucket.get(key)
                if current is None or priority < current[0]:
                    bucket[key] = (priority, item)
    out = {}
    for cid, bucket in merged.items():
        items = [value[1] for value in bucket.values()]
        items.sort(key=lambda x: (x["start"], x["end"], x["title"].casefold()))
        for item in items:
            item.pop("sourceId", None)
        out[cid] = items
    return out


def run() -> int:
    registry = load(REGISTRY_PATH, {})
    lookup, meta = channel_map()
    signature = channel_signature(meta)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=HORIZON_HOURS)
    previous_status = load(STATUS_PATH, {"sources": []})
    previous_by_id = {x.get("id"): x for x in previous_status.get("sources", []) if x.get("id")}

    sources = [
        s for s in registry.get("epgSources", [])
        if s.get("enabled") and s.get("url")
    ]
    results = []
    failures = []
    source_states = []
    cache_hits = 0
    network_fetches = 0

    for source in sorted(sources, key=lambda x: int(x.get("priority", 9999))):
        started = time.perf_counter()
        old = previous_by_id.get(source["id"], {})
        failures_count = int(old.get("consecutiveFailures", 0))
        cached = load_cache(source, signature, now, horizon)
        try:
            body, http_status, response_headers = fetch_xml(source, cached)
            if body is None and cached is not None:
                schedules = cached["schedules"]
                stats = {"channelsMatched": len(schedules), "programsMatched": sum(map(len, schedules.values()))}
                cache_hits += 1
            else:
                if body is None:
                    raise RuntimeError("HTTP 304 received without a valid cache")
                network_fetches += 1
                schedules, stats = parse_source(body, source["id"], lookup, now, horizon)
                save_cache(source, signature, schedules, response_headers)
            latency = round((time.perf_counter() - started) * 1000, 2)
            source_state = {
                "id": source["id"],
                "priority": source.get("priority"),
                "status": "healthy",
                "lastChecked": now.isoformat().replace("+00:00", "Z"),
                "latencyMs": latency,
                "httpStatus": http_status,
                "bytes": len(body) if body is not None else None,
                "consecutiveFailures": 0,
                "cacheHit": body is None,
                "stats": stats,
                "error": None,
            }
            results.append((schedules, source))
            source_states.append(source_state)
            failures_count = 0
        except Exception as exc:
            # If the network source is temporarily unavailable, keep the most
            # recent parsed cache as a stale-but-usable fallback. This prevents
            # one transient outage from deleting the user's EPG.
            stale = load(cache_path(source["id"]), None)
            stale_schedules = None
            if isinstance(stale, dict) and isinstance(stale.get("schedules"), dict):
                stale_schedules = filter_window(stale["schedules"], now, horizon)
            if stale_schedules:
                failures_count += 1
                source_state = {
                    "id": source["id"],
                    "priority": source.get("priority"),
                    "status": "degraded" if failures_count < MAX_FAILURES_FOR_OFFLINE else "offline",
                    "lastChecked": now.isoformat().replace("+00:00", "Z"),
                    "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                    "httpStatus": getattr(exc, "code", None),
                    "consecutiveFailures": failures_count,
                    "cacheHit": True,
                    "staleCache": True,
                    "stats": {"channelsMatched": len(stale_schedules), "programsMatched": sum(map(len, stale_schedules.values()))},
                    "error": str(exc)[:500],
                }
                results.append((stale_schedules, source))
                source_states.append(source_state)
                continue
            failures_count += 1
            health_status = classify(failures_count)
            message = str(exc)[:500]
            failure_state = {
                "id": source["id"],
                "priority": source.get("priority"),
                "status": health_status,
                "lastChecked": now.isoformat().replace("+00:00", "Z"),
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "httpStatus": getattr(exc, "code", None),
                "consecutiveFailures": failures_count,
                "cacheHit": False,
                "error": message,
            }
            failures.append(failure_state)
            source_states.append(failure_state)
            continue

    merged = merge_schedules(results)
    channels = [{
        "id": cid,
        "name": info.get("name"),
        "programs": merged.get(cid, []),
    } for cid, info in meta.items()]
    channels.sort(key=lambda x: (str(x.get("name") or "").casefold(), x["id"]))

    matched = sum(bool(x["programs"]) for x in channels)
    total_programs = sum(len(x["programs"]) for x in channels)
    healthy = len(results)
    failed = len(failures)

    status_value = "healthy" if healthy and not failed else ("degraded" if healthy else "offline")
    output = {
        "schemaVersion": "1.1.0",
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
            "cache": "conditional-http-plus-parsed-cache",
            "cacheTtlHours": CACHE_TTL_HOURS,
            "expiredProgramsDiscarded": True,
            "clientProcessesXmltv": False,
        },
        "stats": {
            "sourcesConfigured": len(sources),
            "sourcesHealthy": healthy,
            "sourcesFailed": failed,
            "cacheHits": cache_hits,
            "networkFetches": network_fetches,
            "channelsKnown": len(channels),
            "channelsWithPrograms": matched,
            "channelsWithoutPrograms": len(channels) - matched,
            "programs": total_programs,
        },
        "channels": channels,
    }
    save(OUTPUT_PATH, output)

    detailed = source_states

    status = {
        "schemaVersion": "1.1.0",
        "generatedAt": output["generatedAt"],
        "status": status_value,
        "sources": detailed,
        "stats": output["stats"],
        "cache": {
            "directory": "CineHUB_Data/.cache/epg",
            "ttlHours": CACHE_TTL_HOURS,
            "conditionalRequestsEnabled": True,
        },
    }
    save(STATUS_PATH, status)
    print(json.dumps(status["stats"], ensure_ascii=False, indent=2))
    return 0 if healthy or not sources else 1


if __name__ == "__main__":
    raise SystemExit(run())
