import unittest

from sync_epg_sources import sync_sources


class SyncEPGSourcesTests(unittest.TestCase):
    def test_syncs_enabled_xmltv_sources_and_removes_known_404_entries(self):
        local = {
            "registryVersion": 4,
            "epgSources": [
                {"id": "brazil-tv-epg", "url": "https://old.example/epg.xml", "enabled": True, "priority": 1},
                {"id": "iptv-org-br-mi-tv", "url": "https://invalid.example/feed.xml", "enabled": True, "priority": 4},
                {"id": "local-test", "url": "https://local.example/feed.xml", "enabled": True, "priority": 50},
            ],
        }
        acervo = {"sources": [
            {"id": "brazil-tv-epg", "name": "Combined", "format": "xmltv", "url": "https://feed.example/combined.xml", "enabled": True, "priority": 25},
            {"id": "html-guide", "name": "HTML guide", "format": "html", "url": "https://example.org", "enabled": True, "priority": 10},
            {"id": "disabled-feed", "format": "xmltv", "url": "https://example.org/off.xml", "enabled": False, "priority": 90},
        ]}
        result = sync_sources(local, acervo)
        sources = result["epgSources"]
        by_id = {x["id"]: x for x in sources}
        self.assertEqual(by_id["brazil-tv-epg"]["url"], "https://feed.example/combined.xml")
        self.assertNotIn("iptv-org-br-mi-tv", by_id)
        self.assertIn("local-test", by_id)
        self.assertNotIn("html-guide", by_id)
        self.assertNotIn("disabled-feed", by_id)
        self.assertEqual([x["priority"] for x in sources], sorted(x["priority"] for x in sources))


if __name__ == "__main__":
    unittest.main()
