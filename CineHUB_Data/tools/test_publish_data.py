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
            self.assertEqual(publish_data.sha256(p), publish_data.sha256(p))

    def test_required_outputs_are_defined(self):
        self.assertIn("status.json", publish_data.REQUIRED)
        self.assertIn("channels/resolved.json", publish_data.REQUIRED)
        self.assertIn("catalog/manifest.json", publish_data.REQUIRED)

    def test_build_creates_publication_and_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            out = root / "out"
            status = data / "status"
            normalized = data / "normalized"
            resolved = data / "resolved"
            catalog = data / "catalog"
            for directory in (status, normalized, resolved, catalog):
                directory.mkdir(parents=True)

            (status / "data-status.json").write_text(
                json.dumps({"status": "no_changes", "healthChecks": {"total": 1, "healthy": 1}}),
                encoding="utf-8",
            )
            (data / "sources.json").write_text("{}", encoding="utf-8")
            (normalized / "channels.json").write_text("{}", encoding="utf-8")
            (resolved / "channels.json").write_text("{}", encoding="utf-8")

            files = {
                "status.json": status / "data-status.json",
                "sources.json": data / "sources.json",
                "channels/normalized.json": normalized / "channels.json",
                "channels/resolved.json": resolved / "channels.json",
                "catalog/manifest.json": catalog / "catalog-manifest.json",
                "catalog/movies.index.json": catalog / "movies.index.json",
                "catalog/series.index.json": catalog / "series.index.json",
                "catalog/metadata.json": catalog / "metadata.json",
            }
            for path in list(files.values())[4:]:
                path.write_text("{}", encoding="utf-8")

            with patch.object(publish_data, "DATA", data),                  patch.object(publish_data, "OUT", out),                  patch.object(publish_data, "FILES", files),                  patch.object(publish_data, "REQUIRED", set(files)):
                first = publish_data.build()
                first_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
                first_status = json.loads((out / "status-public.json").read_text(encoding="utf-8"))
                second = publish_data.build()
                second_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
                second_status = json.loads((out / "status-public.json").read_text(encoding="utf-8"))

            self.assertEqual(first["datasets"], second["datasets"])
            self.assertEqual(first_manifest["generatedAt"], second_manifest["generatedAt"])
            self.assertEqual(first_status["updatedAt"], second_status["updatedAt"])
            self.assertTrue((out / "status-public.json").is_file())

    def test_build_fails_without_required_outputs(self):
        with patch.object(publish_data, "FILES", {
            "status.json": Path("/definitely/missing/status.json"),
        }), patch.object(publish_data, "REQUIRED", {"status.json"}):
            with self.assertRaises(SystemExit):
                publish_data.build()


if __name__ == "__main__":
    unittest.main()
