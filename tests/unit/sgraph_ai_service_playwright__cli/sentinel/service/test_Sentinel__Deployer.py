# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Deployer (full lifecycle, no AWS, no network)
# Drives create → status → destroy/teardown through the *__In_Memory client doubles.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Deployer__In_Memory import new_in_memory_deployer
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Deploy__Request        import Schema__Sentinel__Deploy__Request


def _create(d):
    return d.create(Schema__Sentinel__Deploy__Request(region='us-east-1'))


class TestCreate:
    def test_create_returns_all_components(self):
        d    = new_in_memory_deployer()
        resp = _create(d)
        assert str(resp.distribution_id) != ''
        assert 'function' in str(resp.cf_function_arn)
        assert str(resp.lambda_edge_arn).endswith(':1')                              # numbered L@E version ARN
        assert str(resp.log_bucket).startswith('sg-sentinel-logs-')
        assert str(resp.status) == 'created'

    def test_create_associates_cf_function_on_viewer_request(self):
        d       = new_in_memory_deployer()
        dist_id = str(_create(d).distribution_id)
        assert len(d.cf_client.get_function_associations(dist_id, 'viewer-request')) == 1

    def test_create_associates_lambda_edge_on_origin_request_with_version_arn(self):
        d       = new_in_memory_deployer()
        dist_id = str(_create(d).distribution_id)
        assocs  = d.cf_client.get_lambda_edge_associations(dist_id, 'origin-request')
        assert len(assocs) == 1
        assert assocs[0].endswith(':1')                                              # CloudFront rejects $LATEST — must be numbered

    def test_create_makes_the_log_bucket(self):
        d = new_in_memory_deployer()
        _create(d)
        assert any('sg-sentinel-logs' in b for b in d.s3_client._bucket_store)


class TestStatus:
    def test_status_present_after_create(self):
        d = new_in_memory_deployer()
        _create(d)
        info = d.status()
        assert info['l1_function'] is True
        assert info['l2_lambda']   is True


class TestDestroyTeardown:
    def test_destroy_removes_edge_resources_keeps_bucket(self):
        d       = new_in_memory_deployer()
        resp    = _create(d)
        bucket  = str(resp.log_bucket)
        d.destroy(str(resp.distribution_id))
        info = d.status()
        assert info['l1_function'] is False
        assert info['l2_lambda']   is False
        assert any(bucket == b for b in d.s3_client._bucket_store)                   # bucket kept

    def test_teardown_leaves_no_orphans(self):
        d      = new_in_memory_deployer()
        resp   = _create(d)
        bucket = str(resp.log_bucket)
        d.teardown(str(resp.distribution_id), log_bucket=bucket)
        assert d.status()['l1_function'] is False
        assert d.status()['l2_lambda']   is False
        assert bucket not in d.s3_client._bucket_store                               # bucket gone
        assert len(d.cf_client.list_distributions()) == 0                            # distribution gone

    def test_teardown_empties_bucket_with_records_first(self):
        d      = new_in_memory_deployer()
        resp   = _create(d)
        bucket = str(resp.log_bucket)
        d.s3_client.put_object(bucket, 'sentinel/2026/01/01/00/sn-x.json', b'{}')    # a log object exists
        d.teardown(str(resp.distribution_id), log_bucket=bucket)
        assert bucket not in d.s3_client._bucket_store                               # emptied + deleted regardless
