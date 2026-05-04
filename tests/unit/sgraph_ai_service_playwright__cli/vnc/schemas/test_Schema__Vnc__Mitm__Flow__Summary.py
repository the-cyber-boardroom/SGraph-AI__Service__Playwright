# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Vnc__Mitm__Flow__Summary
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary import List__Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary import Schema__Vnc__Mitm__Flow__Summary


class test_Schema__Vnc__Mitm__Flow__Summary(TestCase):

    def test__defaults(self):
        f = Schema__Vnc__Mitm__Flow__Summary()
        assert str(f.flow_id)        == ''
        assert str(f.method)         == ''
        assert str(f.url)            == ''
        assert f.status_code         == 0
        assert str(f.intercepted_at) == ''

    def test__round_trip_via_json(self):
        f = Schema__Vnc__Mitm__Flow__Summary(flow_id='abc123def456', method='GET',
                                              url='https://example.com/api',
                                              status_code=200,
                                              intercepted_at='2026-04-29T10:00:00Z')
        again = Schema__Vnc__Mitm__Flow__Summary.from_json(f.json())
        assert str(again.flow_id)     == 'abc123def456'
        assert str(again.method)      == 'GET'
        assert str(again.url)         == 'https://example.com/api'
        assert again.status_code      == 200


class test_List__Schema__Vnc__Mitm__Flow__Summary(TestCase):

    def test__expected_type(self):
        assert List__Schema__Vnc__Mitm__Flow__Summary.expected_type is Schema__Vnc__Mitm__Flow__Summary

    def test__append_and_iterate(self):
        flows = List__Schema__Vnc__Mitm__Flow__Summary()
        flows.append(Schema__Vnc__Mitm__Flow__Summary(flow_id='aaa', method='GET' , url='https://a/'))
        flows.append(Schema__Vnc__Mitm__Flow__Summary(flow_id='bbb', method='POST', url='https://b/'))
        assert len(flows)                  == 2
        assert str(flows[1].method)        == 'POST'
