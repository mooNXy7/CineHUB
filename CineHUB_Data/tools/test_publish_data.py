import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_data


class PublishDataTests(unittest.TestCase):
    def test_sha256_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.txt"
            p.write_text("cinehub", encoding="utf-8")
            first = publish_data.sha256(p)
            second = publish_data.sha256(p)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 64)

    def test_required_outputs_are_defined(self):
        self.assertIn("status.json", publish_data.REQUIRED)
        self.assertIn("channels/resolved.json", publish_data.REQUIRED)
        self.assertIn("catalog/manifest.json", publish_data.REQUIRED)

    def test_build_creates_publication_package(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            root = Path(tmp)\n            data = root / "data"; out = root / "out"\n            status = data / "status"; normalized = data / "normalized"; resolved = data / "resolved"; catalog = data / "catalog"\n            for d in (status, normalized, resolved, catalog): d.mkdir(parents=True)\n            (status / "data-status.json").write_text(json.dumps({"status":"no_changes","healthChecks":{"total":1,"healthy":1}}), encoding="utf-8")\n            (data / "sources.json").write_text("{}") if False else None\n            files = {\n                "status.json": status / "data-status.json",\n                "sources.json": data / "sources.json",\n                "channels/normalized.json": normalized / "channels.json",\n                "channels/resolved.json": resolved / "channels.json",\n                "catalog/manifest.json": catalog / "catalog-manifest.json",\n                "catalog/movies.index.json": catalog / "movies.index.json",\n                "catalog/series.index.json": catalog / "series.index.json",\n                "catalog/metadata.json": catalog / "metadata.json",\n            }\n            (data / "sources.json").write_text("{}", encoding="utf-8")\n            (normalized / "channels.json").write_text("{}", encoding="utf-8")\n            (resolved / "channels.json").write_text("{}", encoding="utf-8")\n            for path in list(files.values())[4:]: path.write_text("{}", encoding="utf-8")\n            with patch.object(publish_data, "DATA", data), patch.object(publish_data, "OUT", out), patch.object(publish_data, "FILES", files), patch.object(publish_data, "REQUIRED", set(files)):\n                first = publish_data.build()\n                first_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))\n                second = publish_data.build()\n                second_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))\n            self.assertEqual(first["datasets"], second["datasets"])\n            self.assertEqual(first_manifest["generatedAt"], second_manifest["generatedAt"])\n            self.assertTrue((out / "status-public.json").is_file())\n\n    def test_build_fails_without_required_outputs(self):
        with patch.object(publish_data, "FILES", {
            "status.json": Path("/definitely/missing/status.json"),
        }), patch.object(publish_data, "REQUIRED", {"status.json"}):
            with self.assertRaises(SystemExit):
                publish_data.build()


if __name__ == "__main__":
    unittest.main()
