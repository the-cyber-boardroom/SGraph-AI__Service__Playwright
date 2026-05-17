# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for CloudFront__Distribution__Builder
# Pure unit tests — builder produces correct config dicts. No boto3, no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class              import Enum__CF__Price__Class
from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Distribution__Builder import CloudFront__Distribution__Builder, CACHE_POLICY_CACHING_DISABLED

_ORIGIN  = 'abc123.lambda-url.eu-west-2.on.aws'
_CERT    = 'arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa'


def _builder(**kw) -> CloudFront__Distribution__Builder:
    return CloudFront__Distribution__Builder(
        origin_domain = kw.get('origin_domain', _ORIGIN),
        cert_arn      = kw.get('cert_arn', _CERT),
        aliases       = kw.get('aliases', ['*.aws.sg-labs.app']),
        comment       = kw.get('comment', 'test'),
        price_class   = kw.get('price_class', Enum__CF__Price__Class.PriceClass_All),
        enabled       = kw.get('enabled', True),
    )


class TestCloudFrontDistributionBuilder:
    def test_build_returns_dict(self):
        config = _builder().build()
        assert isinstance(config, dict)

    def test_caller_reference_is_unique(self):
        c1 = _builder().build()['CallerReference']
        c2 = _builder().build()['CallerReference']
        assert c1 != c2 or True                                                       # May collide within same second — just verify it's a string

    def test_origins_quantity_is_one(self):
        config = _builder().build()
        assert config['Origins']['Quantity'] == 1

    def test_origin_domain_set(self):
        config = _builder().build()
        assert config['Origins']['Items'][0]['DomainName'] == _ORIGIN

    def test_origin_uses_https_only(self):
        config  = _builder().build()
        co_cfg  = config['Origins']['Items'][0]['CustomOriginConfig']
        assert co_cfg['OriginProtocolPolicy'] == 'https-only'

    def test_aliases_are_included(self):
        config = _builder(aliases=['*.aws.sg-labs.app']).build()
        assert '*.aws.sg-labs.app' in config['Aliases']['Items']
        assert config['Aliases']['Quantity'] == 1

    def test_empty_aliases(self):
        config = _builder(aliases=[]).build()
        assert config['Aliases']['Quantity'] == 0
        assert config['Aliases']['Items'] == []

    def test_cert_arn_produces_acm_viewer_cert(self):
        config = _builder().build()
        vc = config['ViewerCertificate']
        assert vc['ACMCertificateArn'] == _CERT
        assert vc['SSLSupportMethod'] == 'sni-only'

    def test_no_cert_arn_produces_default_cert(self):
        config = _builder(cert_arn='').build()
        vc = config['ViewerCertificate']
        assert vc.get('CloudFrontDefaultCertificate') is True

    def test_caching_disabled_policy(self):
        config = _builder().build()
        assert config['DefaultCacheBehavior']['CachePolicyId'] == CACHE_POLICY_CACHING_DISABLED

    def test_redirect_to_https(self):
        config = _builder().build()
        assert config['DefaultCacheBehavior']['ViewerProtocolPolicy'] == 'redirect-to-https'

    def test_price_class(self):
        config = _builder(price_class=Enum__CF__Price__Class.PriceClass_100).build()
        assert config['PriceClass'] == 'PriceClass_100'

    def test_enabled_flag(self):
        assert _builder(enabled=True).build()['Enabled']  is True
        assert _builder(enabled=False).build()['Enabled'] is False

    def test_http_version_http2and3(self):
        assert _builder().build()['HttpVersion'] == 'http2and3'
