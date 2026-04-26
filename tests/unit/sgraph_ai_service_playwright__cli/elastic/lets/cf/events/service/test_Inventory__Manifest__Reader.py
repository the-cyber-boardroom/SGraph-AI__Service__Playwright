# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__Manifest__Reader
# Pins the in-memory subclass behaviour: call-args captured, fixture docs
# returned, top_n cap respected.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader__In_Memory import Inventory__Manifest__Reader__In_Memory


def doc(etag: str, key: str = 'k.gz', size: int = 100) -> dict:
    return {'bucket': 'b', 'key': key, 'etag': etag, 'size_bytes': size, 'delivery_at': '2026-04-26T00:00:00.000Z'}


class test_Inventory__Manifest__Reader(TestCase):

    def test_starts_with_no_calls(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[],
                                                          list_calls=[],
                                                          fixture_response=())
        assert reader.list_calls == []

    def test_returns_fixture_docs(self):
        docs_in = [doc('e1', 'a.gz'), doc('e2', 'b.gz')]
        reader  = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=docs_in,
                                                           list_calls=[],
                                                           fixture_response=())
        result, status, err = reader.list_unprocessed(base_url='https://x', username='u', password='p')
        assert len(result) == 2
        assert result[0]['etag'] == 'e1'
        assert status == 200
        assert err == ''

    def test_call_args_captured(self):
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[],
                                                          list_calls=[],
                                                          fixture_response=())
        reader.list_unprocessed(base_url='https://x', username='u', password='p', top_n=42)
        assert reader.list_calls == [('https://x', 42)]

    def test_top_n_caps_fixture(self):                                              # When fixture has more docs than top_n, the slice respects the cap
        docs_in = [doc(f'e{i}') for i in range(10)]
        reader  = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=docs_in,
                                                           list_calls=[],
                                                           fixture_response=())
        result, _, _ = reader.list_unprocessed(base_url='x', username='u', password='p', top_n=3)
        assert len(result) == 3

    def test_fixture_response_overrides(self):                                      # When fixture_response is set, ignore fixture_unprocessed_docs
        reader = Inventory__Manifest__Reader__In_Memory(fixture_unprocessed_docs=[doc('ignored')],
                                                          list_calls=[],
                                                          fixture_response=([], 503, 'cluster red'))
        result, status, err = reader.list_unprocessed(base_url='x', username='u', password='p')
        assert result == []
        assert status == 503
        assert 'cluster red' in err
