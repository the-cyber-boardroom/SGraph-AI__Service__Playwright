# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__Smart_Verify
# Covers all three decision paths: NEW_NAME, UPSERT, DELETE.
# All dependencies are real subclasses with in-memory seams.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Dns__Check__Mode              import Enum__Dns__Check__Mode
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type          import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Smart_Verify__Decision        import Enum__Smart_Verify__Decision
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dig__Result               import Schema__Dig__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dns__Check__Result        import Schema__Dns__Check__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Record           import Schema__Route53__Record
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Decision    import Schema__Smart_Verify__Decision
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Smart_Verify__Result      import Schema__Smart_Verify__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner                       import Dig__Runner
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Authoritative__Checker   import Route53__Authoritative__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client              import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Check__Orchestrator      import Route53__Check__Orchestrator
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Public_Resolver__Checker import Route53__Public_Resolver__Checker
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Smart_Verify             import Route53__Smart_Verify

# ── Fake helpers ──────────────────────────────────────────────────────────────

_ZONE_ID     = 'Z01FAKE'
_NAME        = 'test.sgraph.ai'
_RTYPE       = 'A'
_IP          = '203.0.113.5'
_OLD_IP      = '10.0.0.1'
_PRIOR_TTL   = 300

_NS_SERVERS  = ['ns-1.awsdns-1.com', 'ns-2.awsdns-2.net']


class _Fake_Dig__Runner(Dig__Runner):
    answers: dict                                                                 # ip-of-ns → list of returned values

    def run(self, nameserver, name, rtype, no_recurse=False, timeout=5):
        values = self.answers.get(nameserver, [])
        return Schema__Dig__Result(nameserver=nameserver, name=name, rtype=rtype,
                                   values=values, exit_code=0, error='', duration_ms=1)


class _Fake_Boto3_Client:
    existing_record = None                                                       # Set to a raw dict to simulate an existing record

    def get_hosted_zone(self, Id):
        return {'DelegationSet': {'NameServers': _NS_SERVERS}}

    def get_paginator(self, operation):
        if operation == 'list_resource_record_sets':
            rrs = []
            if self.existing_record:
                rrs.append(self.existing_record)
            return _FakePaginator([{'ResourceRecordSets': rrs}])
        return _FakePaginator([{'HostedZones': []}])

    def change_resource_record_sets(self, **kwargs):
        return {'ChangeInfo': {'Id': '/change/CFAKE123', 'Status': 'PENDING',
                                'SubmittedAt': '2026-05-15T00:00:00Z'}}


class _FakePaginator:
    def __init__(self, pages): self._pages = pages
    def paginate(self, **kwargs): return iter(self._pages)


class _Fake_Route53__AWS__Client(Route53__AWS__Client):
    boto3_stub: _Fake_Boto3_Client = None

    def client(self): return self.boto3_stub


def _build_smart_verify(boto3_stub) -> Route53__Smart_Verify:
    r53_client = _Fake_Route53__AWS__Client(boto3_stub=boto3_stub)
    dig        = _Fake_Dig__Runner(answers={ns: [_IP] for ns in _NS_SERVERS})
    auth       = Route53__Authoritative__Checker(dig_runner=dig, r53_client=r53_client)
    pub        = Route53__Public_Resolver__Checker(
        dig_runner = dig,
        resolvers  = ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4', '9.9.9.9', '94.140.14.14'],
    )
    orch = Route53__Check__Orchestrator(authoritative_checker=auth,
                                        public_resolver_checker=pub)
    return Route53__Smart_Verify(r53_client=r53_client, orchestrator=orch)


def _raw_record(name, rtype, ip, ttl):
    return {'Name': name + '.', 'Type': rtype, 'TTL': ttl,
            'ResourceRecords': [{'Value': ip}]}


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__Smart_Verify(TestCase):

    # ── decide_before_add ─────────────────────────────────────────────────────

    def test__decide_before_add__new_name__no_existing_record(self):
        stub       = _Fake_Boto3_Client()
        stub.existing_record = None
        smart      = _build_smart_verify(stub)
        decision   = smart.decide_before_add(_ZONE_ID, _NAME, Enum__Route53__Record_Type.A)
        assert decision.decision    == Enum__Smart_Verify__Decision.NEW_NAME
        assert decision.prior_ttl   == 0
        assert decision.prior_values == []

    def test__decide_before_add__upsert__existing_record_found(self):
        stub       = _Fake_Boto3_Client()
        stub.existing_record = _raw_record(_NAME, _RTYPE, _OLD_IP, _PRIOR_TTL)
        smart    = _build_smart_verify(stub)
        decision = smart.decide_before_add(_ZONE_ID, _NAME, Enum__Route53__Record_Type.A)
        assert decision.decision    == Enum__Smart_Verify__Decision.UPSERT
        assert decision.prior_ttl   == _PRIOR_TTL
        assert _OLD_IP in decision.prior_values

    # ── verify_after_mutation — NEW_NAME ─────────────────────────────────────

    def test__verify_after_mutation__new_name__runs_both_checks(self):
        stub   = _Fake_Boto3_Client()
        smart  = _build_smart_verify(stub)
        dec    = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.NEW_NAME,
                                                prior_ttl   = 0                                    ,
                                                prior_values= []                                   )
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE, expected=_IP)
        assert isinstance(result, Schema__Smart_Verify__Result)
        assert result.decision        == Enum__Smart_Verify__Decision.NEW_NAME
        assert result.skipped_public  is False
        assert result.public_resolvers is not None
        assert result.skip_message    == ''

    def test__verify_after_mutation__new_name__auth_check_present(self):
        stub   = _Fake_Boto3_Client()
        smart  = _build_smart_verify(stub)
        dec    = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.NEW_NAME,
                                                prior_ttl   = 0, prior_values=[])
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE, expected=_IP)
        assert isinstance(result.authoritative, Schema__Dns__Check__Result)
        assert result.authoritative.mode == Enum__Dns__Check__Mode.AUTHORITATIVE

    # ── verify_after_mutation — UPSERT ────────────────────────────────────────

    def test__verify_after_mutation__upsert__skips_public_resolvers(self):
        stub  = _Fake_Boto3_Client()
        smart = _build_smart_verify(stub)
        dec   = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.UPSERT,
                                               prior_ttl   = _PRIOR_TTL                         ,
                                               prior_values= [_OLD_IP]                          )
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE, expected=_IP)
        assert result.skipped_public   is True
        assert result.public_resolvers is None
        assert result.skip_message     != ''

    def test__verify_after_mutation__upsert__skip_message_contains_prior_ttl(self):
        stub  = _Fake_Boto3_Client()
        smart = _build_smart_verify(stub)
        dec   = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.UPSERT,
                                               prior_ttl   = _PRIOR_TTL, prior_values=[_OLD_IP])
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE)
        assert str(_PRIOR_TTL) in result.skip_message

    # ── verify_after_mutation — DELETE ────────────────────────────────────────

    def test__verify_after_mutation__delete__skips_public_resolvers(self):
        stub  = _Fake_Boto3_Client()
        smart = _build_smart_verify(stub)
        dec   = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.DELETE,
                                               prior_ttl   = _PRIOR_TTL                        ,
                                               prior_values= [_OLD_IP]                         )
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE)
        assert result.skipped_public   is True
        assert result.public_resolvers is None

    def test__verify_after_mutation__delete__skip_message_correct(self):
        stub  = _Fake_Boto3_Client()
        smart = _build_smart_verify(stub)
        dec   = Schema__Smart_Verify__Decision(decision    = Enum__Smart_Verify__Decision.DELETE,
                                               prior_ttl   = _PRIOR_TTL, prior_values=[_OLD_IP])
        result = smart.verify_after_mutation(dec, _ZONE_ID, _NAME, _RTYPE)
        assert 'deletion' in result.skip_message.lower()
        assert str(_PRIOR_TTL) in result.skip_message
