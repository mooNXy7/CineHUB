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

    def test_build_fails_without_required_outputs(self):
        with patch.object(publish_data, "FILES", {
            "status.json": Path("/definitely/missing/status.json"),
        }), patch.object(publish_data, "REQUIRED", {"status.json"}):
            with self.assertRaises(SystemExit):
                publish_data.build()


if __name__ == "__main__":
    unittest.main()
