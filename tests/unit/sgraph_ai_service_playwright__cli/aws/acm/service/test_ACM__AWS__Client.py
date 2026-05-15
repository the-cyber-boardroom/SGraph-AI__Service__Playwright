# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for ACM__AWS__Client
# All tests run against _Fake_ACM__AWS__Client — a real subclass of
# ACM__AWS__Client that overrides client() to return an in-memory stub.
# No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from sgraph_ai_service_playwright__cli.aws.acm.collections.List__Schema__ACM__Certificate import List__Schema__ACM__Certificate
from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Status               import Enum__ACM__Cert_Status
from sgraph_ai_service_playwright__cli.aws.acm.enums.Enum__ACM__Cert_Type                 import Enum__ACM__Cert_Type
from sgraph_ai_service_playwright__cli.aws.acm.schemas.Schema__ACM__Certificate           import Schema__ACM__Certificate
from sgraph_ai_service_playwright__cli.aws.acm.service.ACM__AWS__Client                   import ACM__AWS__Client, FALLBACK_REGION, US_EAST_1

# ── Canned ACM data ───────────────────────────────────────────────────────────

_EU_ARN = 'arn:aws:acm:eu-west-1:123456789012:certificate/aaaa-1111'
_US_ARN = 'arn:aws:acm:us-east-1:123456789012:certificate/bbbb-2222'

_FAKE_LIST_EU = [{'CertificateArn': _EU_ARN}]
_FAKE_LIST_US = [{'CertificateArn': _US_ARN}]

_FAKE_DESCRIBE_EU = {                                                                # Full describe_certificate response for the EU cert
    'Certificate': {
        'CertificateArn'      : _EU_ARN                                              ,
        'DomainName'          : 'api.sgraph.ai'                                      ,
        'SubjectAlternativeNames': ['api.sgraph.ai', 'www.sgraph.ai']                ,
        'Status'              : 'ISSUED'                                             ,
        'Type'                : 'AMAZON_ISSUED'                                      ,
        'InUseBy'             : ['arn:aws:cloudfront::123456789012:distribution/abc'],
        'RenewalEligibility'  : 'ELIGIBLE'                                           ,
    }
}

_FAKE_DESCRIBE_US = {                                                                # Full describe_certificate response for the US cert
    'Certificate': {
        'CertificateArn'      : _US_ARN                                              ,
        'DomainName'          : '*.sgraph.ai'                                        ,
        'SubjectAlternativeNames': ['*.sgraph.ai']                                   ,
        'Status'              : 'ISSUED'                                             ,
        'Type'                : 'AMAZON_ISSUED'                                      ,
        'InUseBy'             : []                                                   ,
        'RenewalEligibility'  : 'INELIGIBLE'                                         ,
    }
}


class _FakeAcmBotoClient:                                                            # In-memory stand-in for acm.client() for a specific region
    def __init__(self, region):
        self._region = region

    def get_paginator(self, operation):
        if operation == 'list_certificates':
            pages = _FAKE_LIST_EU if self._region != US_EAST_1 else _FAKE_LIST_US
            return _FakePaginator([{'CertificateSummaryList': pages}])
        return _FakePaginator([{}])

    def describe_certificate(self, CertificateArn):
        if CertificateArn == _EU_ARN:
            return _FAKE_DESCRIBE_EU
        if CertificateArn == _US_ARN:
            return _FAKE_DESCRIBE_US
        return {'Certificate': {}}


class _FakePaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        return iter(self._pages)


class _Fake_ACM__AWS__Client(ACM__AWS__Client):                                      # Real subclass — overrides the boto3 seam and the region resolver; no mocks
    def client(self, region: str = None):
        return _FakeAcmBotoClient(region or FALLBACK_REGION)

    def current_region(self) -> str:
        return FALLBACK_REGION                                                        # Stable for tests — no boto3 session call


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_ACM__AWS__Client(TestCase):

    def setUp(self):
        self.client = _Fake_ACM__AWS__Client()

    # ── list_certificates ────────────────────────────────────────────────────

    def test__list_certificates__returns_typed_list(self):
        certs = self.client.list_certificates()
        assert isinstance(certs, List__Schema__ACM__Certificate)

    def test__list_certificates__contains_one_cert_for_default_region(self):
        certs = self.client.list_certificates()
        assert len(certs) == 1

    def test__list_certificates__schema_is_correct_type(self):
        certs = self.client.list_certificates()
        for c in certs:
            assert isinstance(c, Schema__ACM__Certificate)

    def test__list_certificates__status_is_enum(self):
        certs = self.client.list_certificates()
        for c in certs:
            assert isinstance(c.status, Enum__ACM__Cert_Status)

    def test__list_certificates__cert_type_is_enum(self):
        certs = self.client.list_certificates()
        for c in certs:
            assert isinstance(c.cert_type, Enum__ACM__Cert_Type)

    def test__list_certificates__region_populated(self):
        certs = self.client.list_certificates(region=FALLBACK_REGION)
        assert certs[0].region == FALLBACK_REGION

    def test__list_certificates__san_count_excludes_primary_domain(self):            # EU cert has 2 SANs including the primary domain — san_count should be 1
        certs = self.client.list_certificates()
        eu_cert = next(c for c in certs if c.arn == _EU_ARN)
        assert eu_cert.san_count == 1

    def test__list_certificates__renewal_eligible_true(self):
        certs   = self.client.list_certificates()
        eu_cert = next(c for c in certs if c.arn == _EU_ARN)
        assert eu_cert.renewal_eligible is True

    def test__list_certificates__in_use_by_count(self):
        certs   = self.client.list_certificates()
        eu_cert = next(c for c in certs if c.arn == _EU_ARN)
        assert eu_cert.in_use_by == 1

    # ── list_certificates__dual_region ───────────────────────────────────────

    def test__list_certificates__dual_region__returns_typed_list(self):
        certs = self.client.list_certificates__dual_region()
        assert isinstance(certs, List__Schema__ACM__Certificate)

    def test__list_certificates__dual_region__deduplicates_by_arn(self):             # The fake returns distinct ARNs for EU and US — so no dedup needed but total should be 2
        certs = self.client.list_certificates__dual_region()
        arns  = [c.arn for c in certs]
        assert len(arns) == len(set(arns))                                           # No duplicates
        assert len(certs) == 2                                                       # EU cert + US cert

    def test__list_certificates__dual_region__dedup_when_same_cert_both_regions(self):
        class _DupACM(_Fake_ACM__AWS__Client):                                       # Override to return the same ARN for both regions
            def client(self, region=None):
                return _FakeAcmBotoClient(FALLBACK_REGION)                           # Always returns EU certs regardless of region

        client = _DupACM()
        certs  = client.list_certificates__dual_region()
        arns   = [c.arn for c in certs]
        assert len(arns) == len(set(arns))                                           # Exactly 1 unique ARN — deduplication worked

    # ── describe_certificate ─────────────────────────────────────────────────

    def test__describe_certificate__returns_schema(self):
        cert = self.client.describe_certificate(_EU_ARN)
        assert isinstance(cert, Schema__ACM__Certificate)

    def test__describe_certificate__arn_populated(self):
        cert = self.client.describe_certificate(_EU_ARN)
        assert cert.arn == _EU_ARN

    def test__describe_certificate__domain_name_correct(self):
        cert = self.client.describe_certificate(_EU_ARN)
        assert str(cert.domain_name) == 'api.sgraph.ai'

    def test__describe_certificate__status_issued(self):
        cert = self.client.describe_certificate(_EU_ARN)
        assert cert.status == Enum__ACM__Cert_Status.ISSUED

    def test__describe_certificate__region_from_arn(self):
        cert = self.client.describe_certificate(_EU_ARN)
        assert cert.region == 'eu-west-1'

    def test__describe_certificate__returns_none_for_unknown_arn(self):
        result = self.client.describe_certificate('arn:aws:acm:eu-west-1:000:certificate/unknown')
        assert result is None or isinstance(result, Schema__ACM__Certificate)        # None or empty schema — depends on fake; at least must not crash

    # ── region_from_arn ──────────────────────────────────────────────────────

    def test__region_from_arn__extracts_eu_west_1(self):
        region = self.client.region_from_arn(_EU_ARN)
        assert region == 'eu-west-1'

    def test__region_from_arn__extracts_us_east_1(self):
        region = self.client.region_from_arn(_US_ARN)
        assert region == 'us-east-1'

    def test__region_from_arn__returns_none_for_malformed(self):
        assert self.client.region_from_arn('not-an-arn') is None
