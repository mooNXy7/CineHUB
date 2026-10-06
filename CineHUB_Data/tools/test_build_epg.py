import unittest
from datetime import datetime, timezone

from build_epg import canonical, merge_schedules, parse_dt, parse_source


class EPGEngineTests(unittest.TestCase):
    def test_canonical_removes_quality_and_accents(self):
        self.assertEqual(canonical("Glóbó [HD]"), "globo")

    def test_xmltv_timezone_is_normalized_to_utc(self):
        value = parse_dt("20261006090000 -0300")
        self.assertEqual(value, datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc))

    def test_parse_source_matches_id_and_name(self):
        now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
        end = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
        xml = b"""<?xml version="1.0"?>
<tv>
  <channel id="globo.br"><display-name>Globo HD</display-name></channel>
  <programme channel="globo.br" start="20261006130000 +0000" stop="20261006140000 +0000">
    <title>Jornal</title>
  </programme>
</tv>"""
        schedules, stats = parse_source(
            xml, "source-a", {"globo": "channel-globo"}, now, end
        )
        self.assertEqual(stats["channelsMatched"], 1)
        self.assertEqual(schedules["channel-globo"][0]["title"], "Jornal")

    def test_merge_prefers_priority_and_fills_gaps(self):
        source_a = {
            "id": "a",
            "priority": 1,
        }
        source_b = {
            "id": "b",
            "priority": 2,
        }
        item_a = {
            "start": "2026-10-06T13:00:00Z",
            "end": "2026-10-06T14:00:00Z",
            "title": "Jornal",
            "sourceId": "a",
        }
        item_b_same = {
            **item_a,
            "title": "Jornal",
            "sourceId": "b",
        }
        item_b_gap = {
            "start": "2026-10-06T14:00:00Z",
            "end": "2026-10-06T15:00:00Z",
            "title": "Filme",
            "sourceId": "b",
        }
        merged = merge_schedules([
            ({"channel-1": [item_a]}, source_a),
            ({"channel-1": [item_b_same, item_b_gap]}, source_b),
        ])
        self.assertEqual([x["title"] for x in merged["channel-1"]], ["Jornal", "Filme"])
        self.assertNotIn("sourceId", merged["channel-1"][0])


if __name__ == "__main__":
    unittest.main()
