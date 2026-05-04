# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Caller__IP__Detector (opensearch-local)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.opensearch.service.Caller__IP__Detector      import (DEFAULT_TIMEOUT,
                                                                                              DEFAULT_URL    ,
                                                                                              Caller__IP__Detector)


class _Fake_Detector(Caller__IP__Detector):                                         # Real subclass, no mocks
    def __init__(self, raw_response):
        super().__init__()
        self.raw_response = raw_response
    def fetch(self) -> str:
        return self.raw_response


class test_Caller__IP__Detector(TestCase):

    def test__defaults(self):
        det = Caller__IP__Detector()
        assert str(det.url)  == DEFAULT_URL
        assert det.timeout   == DEFAULT_TIMEOUT

    def test_detect__strips_trailing_newline(self):                                  # checkip.amazonaws.com returns '1.2.3.4\n'
        ip = _Fake_Detector('1.2.3.4\n').detect()
        assert isinstance(ip, Safe_Str__IP__Address)
        assert str(ip) == '1.2.3.4'

    def test_detect__rejects_malformed_response(self):                               # Safe_Str__IP__Address regex catches it
        with self.assertRaises(ValueError):
            _Fake_Detector('not-an-ip').detect()
