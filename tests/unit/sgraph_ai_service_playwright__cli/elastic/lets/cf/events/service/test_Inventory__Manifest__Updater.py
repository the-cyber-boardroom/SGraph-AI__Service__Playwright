# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Manifest__Updater
# Pins both methods: mark_processed (per-file flip to true) and
# reset_all_processed (wipe-time flip back to false).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater__In_Memory import Inventory__Manifest__Updater__In_Memory


class test_mark_processed(TestCase):

    def test_call_args_captured(self):                                              # (base_url, etag, run_id)
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[])
        u.mark_processed(base_url='https://x', username='u', password='p',
                          etag='e71885f47b8c4d4fa930e1c6e7083682',
                          run_id='20260426T120000Z-cf-realtime-events-load-abcd')
        assert u.mark_calls == [('https://x',
                                  'e71885f47b8c4d4fa930e1c6e7083682',
                                  '20260426T120000Z-cf-realtime-events-load-abcd')]

    def test_default_returns_one_updated(self):                                     # Fixture default: 1 inventory doc updated, HTTP 200
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[])
        count, status, err = u.mark_processed(base_url='x', username='u', password='p',
                                                etag='e1', run_id='r1')
        assert count == 1
        assert status == 200
        assert err == ''

    def test_fixture_count_overrides(self):
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[],
                                                      fixture_mark_count=5)
        count, _, _ = u.mark_processed(base_url='x', username='u', password='p',
                                         etag='e1', run_id='r1')
        assert count == 5

    def test_fixture_error_propagates(self):
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[],
                                                      fixture_mark_error='cluster red')
        count, status, err = u.mark_processed(base_url='x', username='u', password='p',
                                                etag='e1', run_id='r1')
        assert count == 0
        assert 'cluster red' in err


class test_reset_all_processed(TestCase):

    def test_call_args_captured(self):                                              # Just (base_url,)
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[])
        u.reset_all_processed(base_url='https://x', username='u', password='p')
        assert u.reset_calls == [('https://x',)]

    def test_fixture_reset_count(self):
        u = Inventory__Manifest__Updater__In_Memory(mark_calls=[], reset_calls=[],
                                                      fixture_reset_count=425)
        count, _, _ = u.reset_all_processed(base_url='x', username='u', password='p')
        assert count == 425
