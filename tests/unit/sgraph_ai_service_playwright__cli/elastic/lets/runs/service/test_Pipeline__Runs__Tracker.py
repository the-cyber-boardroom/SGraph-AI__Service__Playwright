# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Pipeline__Runs__Tracker
# Pins the journal write contract:
#   - index name keys on started_at[:10] (run start day; survives midnight crossings)
#   - bulk-post id_field is 'run_id' (re-recording overwrites)
#   - In_Memory subclass captures the call
#   - Real implementation goes via Inventory__HTTP__Client.bulk_post_with_id
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.runs.enums.Enum__Pipeline__Verb               import Enum__Pipeline__Verb
from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run             import Schema__Pipeline__Run
from sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker           import Pipeline__Runs__Tracker, index_name_for_run

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker__In_Memory          import Pipeline__Runs__Tracker__In_Memory


def make_record(run_id: str = 'run-1', started_at: str = '2026-04-27T10:00:00Z') -> Schema__Pipeline__Run:
    return Schema__Pipeline__Run(run_id     = run_id                          ,
                                  verb       = Enum__Pipeline__Verb.EVENTS_LOAD,
                                  started_at = started_at                      )


# ─── helpers ─────────────────────────────────────────────────────────────────

class test_index_name_for_run(TestCase):

    def test_keys_on_started_at_date_part(self):
        rec = make_record(started_at='2026-04-27T10:00:00Z')
        assert index_name_for_run(rec) == 'sg-pipeline-runs-2026-04-27'

    def test_midnight_crossing_lands_on_start_day(self):                             # A run that started just before midnight UTC keeps that date even if finished_at is tomorrow
        rec = make_record(started_at='2026-04-26T23:59:59Z')
        assert index_name_for_run(rec) == 'sg-pipeline-runs-2026-04-26'

    def test_empty_started_at_falls_back_to_epoch(self):                             # Defensive — empty started_at is a bug; don't crash
        rec = make_record(started_at='')
        assert index_name_for_run(rec) == 'sg-pipeline-runs-1970-01-01'


# ─── In_Memory subclass ──────────────────────────────────────────────────────

class test_Pipeline__Runs__Tracker__In_Memory(TestCase):

    def test_captures_call(self):
        tracker = Pipeline__Runs__Tracker__In_Memory(record_calls=[], fixture_response=())
        result  = tracker.record_run(base_url='https://x', username='u', password='p',
                                       record=make_record(run_id='r-1'))
        assert result == (1, 0, 0, 200, '')
        assert len(tracker.record_calls) == 1
        base_url, snapshot = tracker.record_calls[0]
        assert base_url            == 'https://x'
        assert snapshot['run_id']  == 'r-1'
        assert snapshot['verb']    == 'events-load'

    def test_fixture_response_propagates(self):
        tracker = Pipeline__Runs__Tracker__In_Memory(record_calls=[],
                                                       fixture_response=(0, 0, 1, 503, 'cluster red'))
        result  = tracker.record_run(base_url='x', username='u', password='p', record=make_record())
        assert result == (0, 0, 1, 503, 'cluster red')


# ─── real implementation ─────────────────────────────────────────────────────

class test_Pipeline__Runs__Tracker__real(TestCase):

    def test_bulk_post_uses_run_id_as_doc_id(self):                                  # _id = run_id → re-recording overwrites
        http    = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=(),
                                                       delete_pattern_calls=[], fixture_delete_pattern_response=(),
                                                       count_pattern_calls=[], fixture_count_response=(),
                                                       aggregate_calls=[], fixture_run_buckets=[])
        tracker = Pipeline__Runs__Tracker(http_client=http)
        result  = tracker.record_run(base_url='https://x', username='u', password='p',
                                       record=make_record(run_id='r-1', started_at='2026-04-27T10:00:00Z'))
        assert result == (1, 0, 0, 200, '')                                          # Default In_Memory: every doc reported as created
        assert len(http.bulk_calls) == 1
        base_url, index, count, id_field = http.bulk_calls[0]
        assert base_url == 'https://x'
        assert index    == 'sg-pipeline-runs-2026-04-27'
        assert count    == 1                                                          # One journal doc per call
        assert id_field == 'run_id'                                                   # Re-recording overwrites in place

    def test_per_day_index_drives_correct_target(self):                              # Two runs on different days → two different indices
        http    = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=(),
                                                       delete_pattern_calls=[], fixture_delete_pattern_response=(),
                                                       count_pattern_calls=[], fixture_count_response=(),
                                                       aggregate_calls=[], fixture_run_buckets=[])
        tracker = Pipeline__Runs__Tracker(http_client=http)
        tracker.record_run(base_url='x', username='u', password='p',
                            record=make_record(run_id='r-1', started_at='2026-04-26T01:00:00Z'))
        tracker.record_run(base_url='x', username='u', password='p',
                            record=make_record(run_id='r-2', started_at='2026-04-27T01:00:00Z'))
        assert [c[1] for c in http.bulk_calls] == ['sg-pipeline-runs-2026-04-26', 'sg-pipeline-runs-2026-04-27']
