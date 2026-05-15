# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__Authoritative__Checker
# Uses a fake Dig__Runner and a fake Route53__AWS__Client so no real boto3 or
# dig calls occur. Tests the agree / disagree logic in check().
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode              import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dig__Result               import Schema__Dig__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result        import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                       import Dig__Runner
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Authoritative__Checker   import Route53__Authoritative__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client              import Route53__AWS__Client

# ── Fake helpers ──────────────────────────────────────────────────────────────

_ZONE_ID      = 'Z01FAKE'
_NS_SERVERS   = ['ns-1.awsdns-1.com', 'ns-2.awsdns-2.net',
                 'ns-3.awsdns-3.org', 'ns-4.awsdns-4.co.uk']
_EXPECTED_IP  = '203.0.113.5'
_OTHER_IP     = '10.0.0.1'


class _Fake_Dig__Runner(Dig__Runner):                                            # Returns configurable per-NS answers; never calls subprocess
    answers: dict                                                                 # nameserver → list of values

    def run(self, nameserver, name, rtype, no_recurse=False, timeout=5):
        values = self.answers.get(nameserver, [])
        return Schema__Dig__Result(nameserver  = nameserver,
                                   name        = name      ,
                                   rtype       = rtype     ,
                                   values      = values    ,
                                   exit_code   = 0         ,
                                   error       = ''        ,
                                   duration_ms = 1         )


class _Fake_Route53__AWS__Client(Route53__AWS__Client):                          # Returns hardcoded NS list via get_hosted_zone
    def client(self):
        return _Fake_Route53_Boto3_Client()


class _Fake_Route53_Boto3_Client:
    def get_hosted_zone(self, Id):
        return {'DelegationSet': {'NameServers': _NS_SERVERS}}

    def get_paginator(self, operation):
        return _FakePaginator([{}])

    def change_resource_record_sets(self, **kwargs):
        return {'ChangeInfo': {'Id': '/change/CFAKE', 'Status': 'PENDING', 'SubmittedAt': '2026-05-15T00:00:00Z'}}


class _FakePaginator:
    def __init__(self, pages): self._pages = pages
    def paginate(self, **kwargs): return iter(self._pages)


def _make_checker(answers: dict) -> Route53__Authoritative__Checker:
    runner = _Fake_Dig__Runner(answers=answers)
    r53    = _Fake_Route53__AWS__Client()
    return Route53__Authoritative__Checker(dig_runner=runner, r53_client=r53)


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__Authoritative__Checker(TestCase):

    def test__check__returns_schema_dns_check_result(self):
        checker = _make_checker({ns: [_EXPECTED_IP] for ns in _NS_SERVERS})
        result  = checker.check(_ZONE_ID, 'test.sgraph.ai', 'A', expected=_EXPECTED_IP)
        assert isinstance(result, Schema__Dns__Check__Result)

    def test__check__mode_is_authoritative(self):
        checker = _make_checker({ns: [_EXPECTED_IP] for ns in _NS_SERVERS})
        result  = checker.check(_ZONE_ID, 'test.sgraph.ai', 'A')
        assert result.mode == Enum__Dns__Check__Mode.AUTHORITATIVE

    def test__check__all_agree__passed_true(self):
        answers = {ns: [_EXPECTED_IP] for ns in _NS_SERVERS}
        checker = _make_checker(answers)
        result  = checker.check(_ZONE_ID, 'test.sgraph.ai', 'A', expected=_EXPECTED_IP)
        assert result.passed       is True
        assert result.agreed_count == 4
        assert result.total_count  == 4

    def test__check__one_disagrees__passed_false(self):
        answers = {ns: [_EXPECTED_IP] for ns in _NS_SERVERS}
        # Make the last NS return a different IP
        answers[_NS_SERVERS[-1]] = [_OTHER_IP]
        checker = _make_checker(answers)
        result  = checker.check(_ZONE_ID, 'test.sgraph.ai', 'A', expected=_EXPECTED_IP)
        assert result.passed       is False
        assert result.agreed_count == 3
        assert result.total_count  == 4

    def test__check__no_expected__any_answer_counts(self):
        # When expected='', passing means all NS return something
        answers = {ns: [_EXPECTED_IP] for ns in _NS_SERVERS}
        checker = _make_checker(answers)
        result  = checker.check(_ZONE_ID, 'test.sgraph.ai', 'A', expected='')
        assert result.passed is True

    def test__check__no_expected__empty_answer_fails(self):
        answers = {ns: [] for ns in _NS_SERVERS}
        checker = _make_checker(answers)
        result  = checker.check(_ZONE_ID, 'nxdomain.sgraph.ai', 'A', expected='')
        assert result.passed is False

    def test__get_ns_for_zone__strips_trailing_dots(self):
        checker = Route53__Authoritative__Checker(
            dig_runner = _Fake_Dig__Runner(answers={}),
            r53_client = _Fake_Route53__AWS__Client_WithDots(),
        )
        ns_list = checker.get_ns_for_zone(_ZONE_ID)
        for ns in ns_list:
            assert not ns.endswith('.')


class _Fake_Route53_Boto3_Client_WithDots:
    def get_hosted_zone(self, Id):
        return {'DelegationSet': {'NameServers': ['ns-1.awsdns-1.com.', 'ns-2.awsdns-2.net.']}}

    def get_paginator(self, op): return _FakePaginator([{}])
    def change_resource_record_sets(self, **kw): return {'ChangeInfo': {'Id': '/change/C1', 'Status': 'PENDING', 'SubmittedAt': '2026-05-15T00:00:00Z'}}


class _Fake_Route53__AWS__Client_WithDots(Route53__AWS__Client):
    def client(self): return _Fake_Route53_Boto3_Client_WithDots()
