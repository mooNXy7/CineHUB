#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 2 bootstrap updater."""
from __future__ import annotations
import hashlib, json, os, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "CineHUB_Data/sources/registry.json"
MANIFEST_PATH = ROOT / "CineHUB_Data/manifests/data-manifest.json"
STATUS_PATH = ROOT / "CineHUB_Data/status/data-status.json"
TIMEOUT_SECONDS = int(os.environ.get("CINEHUB_DATA_TIMEOUT", "25"))
MAX_BYTES = int(os.environ.get("CINEHUB_DATA_MAX_BYTES", str(25 * 1024 * 1024)))
USER_AGENT = "CineHUB-Data-Engine/2.0 (+https://github.com/mooNXy7/CineHUB)"
RETRIES = 2

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def fetch(url: str) -> tuple[bytes, int, str | None]:
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"})
            with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                chunks, total = [], 0
                while True:
                    chunk = response.read(min(1024 * 1024, MAX_BYTES - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError(f"response exceeds {MAX_BYTES} bytes")
                    chunks.append(chunk)
                return b"".join(chunks), int(response.status), response.headers.get("content-type")
        except HTTPError as exc:
            last_error = exc
            if exc.code in {401, 403, 404}:
                break
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
        if attempt < RETRIES:
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last_error) if last_error else "unknown fetch error")

def update() -> int:
    registry = load_json(REGISTRY_PATH)
    manifest = load_json(MANIFEST_PATH)
    status = load_json(STATUS_PATH)
    timestamp = now_iso()
    content_changed = False
    results = []

    for source in registry.get("sources", []):
        if not source.get("enabled") or source.get("transport") != "remote":
            continue
        url = source.get("url")
        if not url:
            continue
        result = {"id": source.get("id"), "url": url, "checkedAt": timestamp, "changed": False}
        try:
            body, http_status, content_type = fetch(url)
            digest = hashlib.sha256(body).hexdigest()
            old_digest = source.get("contentSha256")
            result.update({"status": "changed" if digest != old_digest else "unchanged",
                           "httpStatus": http_status, "bytes": len(body),
                           "contentType": content_type, "sha256": digest})
            source.update({"lastFetchedAt": timestamp, "lastHttpStatus": http_status,
                           "contentBytes": len(body), "contentSha256": digest,
                           "lastContentType": content_type, "lastFetchError": None})
            if digest != old_digest:
                source["changedAt"] = timestamp
                result["changed"] = True
                content_changed = True
        except Exception as exc:
            message = str(exc)[:500]
            result.update({"status": "error", "error": message})
            source.update({"lastFetchedAt": timestamp, "lastFetchError": message})
            content_changed = True
        results.append(result)

    if content_changed:
        registry["registryVersion"] = int(registry.get("registryVersion", 1)) + 1
        registry.setdefault("refreshPolicy", {})["lastRunAt"] = timestamp
        save_json(REGISTRY_PATH, registry)
        manifest["manifestVersion"] = int(manifest.get("manifestVersion", 1)) + 1
        manifest["generatedAt"] = timestamp
        manifest["generatedBy"] = "CineHUB Data Engine Phase 2"
        manifest.setdefault("publication", {})["automatic"] = True
        save_json(MANIFEST_PATH, manifest)

    status["status"] = "updated" if content_changed else "no_changes"
    status["updatedAt"] = timestamp
    status["engine"] = {"phase": 2, "mode": "remote-source-fingerprint",
                        "lastRunAt": timestamp, "changed": content_changed}
    status["sources"] = {
        "checked": len(results),
        "changed": sum(r["status"] == "changed" for r in results),
        "unchanged": sum(r["status"] == "unchanged" for r in results),
        "errors": sum(r["status"] == "error" for r in results)
    }
    status["lastRun"] = results
    save_json(STATUS_PATH, status)

    print(json.dumps({"status": status["status"], "sourcesChecked": len(results),
                      "changed": content_changed,
                      "sourceChanges": status["sources"]["changed"],
                      "errors": status["sources"]["errors"]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(update())
