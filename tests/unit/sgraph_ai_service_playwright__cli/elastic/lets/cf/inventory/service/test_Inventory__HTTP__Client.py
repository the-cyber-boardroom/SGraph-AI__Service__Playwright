# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Inventory__HTTP__Client
# The In_Memory subclass overrides bulk_post_with_id wholesale, so these tests
# pin behaviour at the override seam: empty docs short-circuit, the call
# arguments are captured, and fixture overrides flow through unchanged.
# No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.collections.List__Schema__S3__Object__Record import List__Schema__S3__Object__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record import Schema__S3__Object__Record

from tests.unit.sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client__In_Memory import Inventory__HTTP__Client__In_Memory


def make_records(n: int) -> List__Schema__S3__Object__Record:
    lst = List__Schema__S3__Object__Record()
    for i in range(n):
        lst.append(Schema__S3__Object__Record(etag=f'{i:032x}'))                    # 32-hex etag — unique per doc
    return lst


class test_Inventory__HTTP__Client(TestCase):

    def test_call_args_captured(self):                                              # Confirms (base_url, index, count, id_field) tuple shape
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        client.bulk_post_with_id(base_url='https://1.2.3.4', username='u', password='p',
                                  index='sg-cf-inventory-2026-04-25', docs=make_records(3),
                                  id_field='etag')
        assert client.bulk_calls == [('https://1.2.3.4', 'sg-cf-inventory-2026-04-25', 3, 'etag')]

    def test_default_fixture_returns_all_created(self):                             # Fixture-mode default: every doc reported as created, HTTP 200
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        created, updated, failed, status, err = client.bulk_post_with_id(
            base_url='https://1.2.3.4', username='u', password='p',
            index='sg-cf-inventory-2026-04-25', docs=make_records(5))
        assert (created, updated, failed, status, err) == (5, 0, 0, 200, '')

    def test_fixture_override_propagates(self):                                     # Tests that need to simulate failure inject their own tuple
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[],
                                                     fixture_response=(0, 0, 5, 503, 'HTTP 503: ES temporarily down'))
        created, updated, failed, status, err = client.bulk_post_with_id(
            base_url='https://1.2.3.4', username='u', password='p',
            index='sg-cf-inventory-2026-04-25', docs=make_records(5))
        assert created == 0
        assert failed  == 5
        assert status  == 503
        assert 'HTTP 503' in err

    def test_empty_docs_short_circuit(self):                                        # Real implementation returns (0, 0, 0, 0, '') without calling request()
        client = Inventory__HTTP__Client__In_Memory(bulk_calls=[], fixture_response=())
        result = client.bulk_post_with_id(base_url='https://x', username='u', password='p',
                                           index='i', docs=List__Schema__S3__Object__Record())
        assert result == (0, 0, 0, 200, '')                                         # In_Memory returns its default with len(docs)=0
        assert client.bulk_calls == [('https://x', 'i', 0, 'etag')]
