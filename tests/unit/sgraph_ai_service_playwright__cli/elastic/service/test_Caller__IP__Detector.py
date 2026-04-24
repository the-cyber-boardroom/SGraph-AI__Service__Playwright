# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Caller__IP__Detector
# Uses Caller__IP__Detector__In_Memory to avoid real HTTP. No mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory import Caller__IP__Detector__In_Memory


class test_Caller__IP__Detector(TestCase):

    def test_detect__returns_safe_str_ip(self):
        detector = Caller__IP__Detector__In_Memory()
        ip       = detector.detect()
        assert type(ip) is Safe_Str__IP__Address
        assert str(ip)  == '203.0.113.42'                                           # Trailing newline stripped by detect()

    def test_detect__rejects_garbage(self):                                         # Primitive regex blocks non-IPv4 returns
        class Bad(Caller__IP__Detector__In_Memory):
            fixture_ip = 'not an ip'
        detector = Bad()
        try:
            detector.detect()
            assert False, 'expected validation error'
        except Exception:
            pass                                                                    # Safe_Str raises a typed validation error
