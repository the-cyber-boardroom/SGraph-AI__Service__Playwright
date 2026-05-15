# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__Local__Checker
# Fakes Dig__Runner with a real Type_Safe subclass — no mocks, no patches.
# Covers expected-match, mismatch, empty-expected, and that the runner is
# invoked with an empty nameserver (host default resolver).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode          import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dig__Result           import Schema__Dig__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result    import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                   import Dig__Runner
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Local__Checker       import Route53__Local__Checker


_NAME  = 'test.sgraph.ai'
_RTYPE = 'A'
_IP    = '203.0.113.5'


# ── Fake Dig__Runner ──────────────────────────────────────────────────────────

class _Fake_Dig__Runner(Dig__Runner):                                                # Records the last call args and returns canned values
    canned_values    : list                                                          # Values to return from .run()
    last_nameserver  : str                                                           # Captured for assertions on the @<ns> arg
    last_no_recurse  : bool                                                          # Captured to ensure the local checker uses default recursion

    def run(self, nameserver, name, rtype, no_recurse=False, timeout=5):
        self.last_nameserver = nameserver
        self.last_no_recurse = no_recurse
        return Schema__Dig__Result(nameserver  = nameserver           ,
                                   name        = name                 ,
                                   rtype       = rtype                ,
                                   values      = list(self.canned_values),
                                   exit_code   = 0                    ,
                                   error       = ''                   ,
                                   duration_ms = 1                    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__Local__Checker(TestCase):

    def test__check__returns_schema_dns_check_result(self):
        dig    = _Fake_Dig__Runner(canned_values=[_IP])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert isinstance(result, Schema__Dns__Check__Result)

    def test__check__mode_is_local(self):
        dig    = _Fake_Dig__Runner(canned_values=[_IP])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert result.mode == Enum__Dns__Check__Mode.LOCAL

    def test__check__total_count_is_one(self):
        dig    = _Fake_Dig__Runner(canned_values=[_IP])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert result.total_count == 1
        assert len(result.results) == 1

    def test__check__expected_match__passed_true(self):
        dig    = _Fake_Dig__Runner(canned_values=[_IP])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert result.passed       is True
        assert result.agreed_count == 1

    def test__check__expected_mismatch__passed_false(self):
        dig    = _Fake_Dig__Runner(canned_values=['10.0.0.1'])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert result.passed       is False
        assert result.agreed_count == 0

    def test__check__empty_expected__nonempty_values__passed_true(self):
        dig    = _Fake_Dig__Runner(canned_values=[_IP])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected='')
        assert result.passed       is True
        assert result.agreed_count == 1

    def test__check__empty_expected__empty_values__passed_false(self):
        dig    = _Fake_Dig__Runner(canned_values=[])
        result = Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected='')
        assert result.passed       is False
        assert result.agreed_count == 0

    def test__check__invokes_dig_with_empty_nameserver(self):                        # Confirms LOCAL mode skips the @<ns> arg via empty string
        dig = _Fake_Dig__Runner(canned_values=[_IP])
        Route53__Local__Checker(dig_runner=dig).check(_NAME, _RTYPE, expected=_IP)
        assert dig.last_nameserver == ''
        assert dig.last_no_recurse is False                                          # Local resolver must recurse — that's its job
