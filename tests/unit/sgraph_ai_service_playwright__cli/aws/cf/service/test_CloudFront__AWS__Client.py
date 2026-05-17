# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for CloudFront__AWS__Client
# All tests use CloudFront__AWS__Client__In_Memory — a real subclass that
# overrides client() to return a dict-backed fake. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Distribution__Status     import Enum__CF__Distribution__Status
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class              import Enum__CF__Price__Class
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name     import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn           import Safe_Str__Cert__Arn
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request      import Schema__CF__Create__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client__In_Memory import CloudFront__AWS__Client__In_Memory

_CERT_ARN = 'arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa'
_ORIGIN   = 'abc123.lambda-url.eu-west-2.on.aws'


def _client() -> CloudFront__AWS__Client__In_Memory:
    return CloudFront__AWS__Client__In_Memory()


def _create_req(**kw) -> Schema__CF__Create__Request:
    return Schema__CF__Create__Request(
        origin_domain = Safe_Str__CF__Domain_Name(kw.get('origin_domain', _ORIGIN)),
        cert_arn      = Safe_Str__Cert__Arn(kw.get('cert_arn', _CERT_ARN)),
        aliases       = kw.get('aliases', ['*.aws.sg-labs.app']),
        comment       = kw.get('comment', 'test dist'),
    )


class TestListDistributions:
    def test_empty_returns_empty_list(self):
        client = _client()
        result = client.list_distributions()
        assert len(result) == 0

    def test_after_create_returns_one(self):
        client = _client()
        client.create_distribution(_create_req())
        result = client.list_distributions()
        assert len(result) == 1

    def test_after_two_creates_returns_two(self):
        client = _client()
        client.create_distribution(_create_req(comment='first'))
        client.create_distribution(_create_req(comment='second'))
        result = client.list_distributions()
        assert len(result) == 2


class TestCreateDistribution:
    def test_create_returns_id_and_domain(self):
        client = _client()
        resp   = client.create_distribution(_create_req())
        assert str(resp.distribution_id) != ''
        assert 'cloudfront.net' in str(resp.domain_name)

    def test_create_status_is_in_progress(self):
        client = _client()
        resp   = client.create_distribution(_create_req())
        assert resp.status == Enum__CF__Distribution__Status.IN_PROGRESS

    def test_create_message_is_created(self):
        client = _client()
        resp   = client.create_distribution(_create_req())
        assert resp.message == 'created'

    def test_create_preserves_aliases(self):
        client  = _client()
        aliases = ['*.aws.sg-labs.app']
        resp    = client.create_distribution(_create_req(aliases=aliases))
        dist    = client.get_distribution(str(resp.distribution_id))
        assert '*.aws.sg-labs.app' in dist.aliases


class TestGetDistribution:
    def test_get_existing(self):
        client = _client()
        cr     = client.create_distribution(_create_req())
        dist   = client.get_distribution(str(cr.distribution_id))
        assert str(dist.distribution_id) == str(cr.distribution_id)

    def test_get_missing_raises(self):
        client = _client()
        try:
            client.get_distribution('ENONEXISTENT')
            assert False, 'expected exception'
        except Exception as e:
            assert 'ENONEXISTENT' in str(e)


class TestDisableDistribution:
    def test_disable_happy_path(self):
        client = _client()
        cr     = client.create_distribution(_create_req())
        dist_id = str(cr.distribution_id)
        resp   = client.disable_distribution(dist_id)
        assert resp.success  is True
        assert resp.message  == 'disabled'

    def test_disable_missing_fails(self):
        client = _client()
        resp   = client.disable_distribution('ENONEXISTENT')
        assert resp.success is False
        assert 'ENONEXISTENT' in resp.message


class TestDeleteDistribution:
    def test_delete_disabled_distribution(self):
        client  = _client()
        cr      = client.create_distribution(_create_req())
        dist_id = str(cr.distribution_id)
        client.disable_distribution(dist_id)
        resp = client.delete_distribution(dist_id)
        assert resp.success is True
        assert resp.message == 'deleted'
        assert len(client.list_distributions()) == 0

    def test_delete_enabled_fails(self):
        client  = _client()
        cr      = client.create_distribution(_create_req())
        dist_id = str(cr.distribution_id)
        resp    = client.delete_distribution(dist_id)
        assert resp.success is False
        assert 'disabled' in resp.message.lower() or 'must be' in resp.message.lower()

    def test_delete_missing_fails(self):
        client = _client()
        resp   = client.delete_distribution('ENONEXISTENT')
        assert resp.success is False


class TestWaitDeployed:
    def test_wait_deployed_succeeds_when_already_deployed(self):
        client  = _client()
        cr      = client.create_distribution(_create_req())
        dist_id = str(cr.distribution_id)
        client.set_deployed(dist_id)
        resp = client.wait_deployed(dist_id, timeout_sec=1, poll_sec=0)
        assert resp.success is True
        assert resp.message == 'deployed'

    def test_wait_deployed_times_out(self):
        client  = _client()
        cr      = client.create_distribution(_create_req())
        dist_id = str(cr.distribution_id)
        resp    = client.wait_deployed(dist_id, timeout_sec=0, poll_sec=0)
        assert resp.success is False
        assert 'timed out' in resp.message
