#!/usr/bin/env python3
"""Mirror enabled XMLTV source definitions from the shared CineHUB ACERVO."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "CineHUB_Data/sources/registry.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sync_sources(registry, acervo):
    current = registry.get("epgSources", [])
    remote = [s for s in acervo.get("sources", [])
              if s.get("enabled") and s.get("format") == "xmltv" and s.get("url")]
    remote_ids = {s["id"] for s in remote}
    # Keep only explicitly local feeds that are not owned by the shared registry.
    preserved = [s for s in current
                 if s.get("id") not in remote_ids
                 and s.get("id") not in {"iptv-org-br-mi-tv", "iptv-com-brazil"}]
    mirrored = []
    for source in remote:
        mirrored.append({
            "id": source["id"],
            "name": source.get("name", source["id"]),
            "kind": "xmltv",
            "scope": "epg",
            "transport": "remote",
            "url": source["url"],
            "enabled": True,
            "priority": int(source.get("priority", 9999)),
            "description": source.get("notes", "Mirrored from the shared CineHUB ACERVO registry."),
            "sourceRegistry": "CineHUB-ACERVO",
        })
    result = sorted(preserved + mirrored, key=lambda x: (int(x.get("priority", 9999)), x.get("id", "")))
    registry["epgSources"] = result
    registry["registryVersion"] = int(registry.get("registryVersion", 1)) + 1
    return registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True, help="Path to ACERVO catalog/epg/sources.json")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()
    registry_path = Path(args.registry)
    registry = load(registry_path)
    acervo = load(args.source_file)
    updated = sync_sources(registry, acervo)
    encoded = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if registry_path.read_text(encoding="utf-8") != encoded:
        registry_path.write_text(encoded, encoding="utf-8")
        print(f"Sincronizadas {len(updated['epgSources'])} fontes XMLTV do ACERVO.")
    else:
        print("Registro EPG já está sincronizado.")


if __name__ == "__main__":
    main()
