# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Events__Run__Summary
# Per-row content of `events list` output. Adds file_count vs the inventory
# version (slice 2 events span multiple .gz files per run).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Run__Summary import Schema__Events__Run__Summary


class test_Schema__Events__Run__Summary(TestCase):

    def test_default_construction(self):
        s = Schema__Events__Run__Summary()
        assert s.event_count    == 0
        assert s.file_count     == 0
        assert s.bytes_total    == 0
        assert s.earliest_event == ''

    def test_with_values(self):
        s = Schema__Events__Run__Summary(pipeline_run_id = 'run-1'              ,
                                           event_count     = 5_000               ,
                                           file_count      = 50                  ,
                                           bytes_total     = 75_000              ,
                                           earliest_event  = '2026-04-25T00:00:20Z',
                                           latest_event    = '2026-04-25T23:59:50Z')
        assert s.event_count    == 5_000
        assert s.file_count     == 50
        assert str(s.latest_event) == '2026-04-25T23:59:50Z'
