# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for CloudFront__Origin__Failover__Builder
# Pure unit tests — builder produces correct OriginGroups dict. No AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__Origin__Failover__Builder import CloudFront__Origin__Failover__Builder


class TestCloudFrontOriginFailoverBuilder:
    def test_build_returns_dict(self):
        b = CloudFront__Origin__Failover__Builder(
            primary_origin_id  = 'ec2-origin',
            fallback_origin_id = 'waker-origin',
        )
        result = b.build()
        assert isinstance(result, dict)

    def test_quantity_is_one(self):
        b      = CloudFront__Origin__Failover__Builder(
            primary_origin_id  = 'ec2-origin',
            fallback_origin_id = 'waker-origin',
        )
        result = b.build()
        assert result['Quantity'] == 1

    def test_group_id_set(self):
        b      = CloudFront__Origin__Failover__Builder(
            group_id           = 'my-group',
            primary_origin_id  = 'ec2-origin',
            fallback_origin_id = 'waker-origin',
        )
        result = b.build()
        assert result['Items'][0]['Id'] == 'my-group'

    def test_primary_and_fallback_origins(self):
        b      = CloudFront__Origin__Failover__Builder(
            primary_origin_id  = 'ec2-origin',
            fallback_origin_id = 'waker-origin',
        )
        result  = b.build()
        members = result['Items'][0]['Members']['Items']
        assert members[0]['OriginId'] == 'ec2-origin'
        assert members[1]['OriginId'] == 'waker-origin'
        assert result['Items'][0]['Members']['Quantity'] == 2

    def test_default_status_codes(self):
        b      = CloudFront__Origin__Failover__Builder(
            primary_origin_id  = 'p',
            fallback_origin_id = 'f',
        )
        result  = b.build()
        codes   = result['Items'][0]['FailoverCriteria']['StatusCodes']['Items']
        assert 500 in codes
        assert 502 in codes
        assert 503 in codes
        assert 504 in codes

    def test_custom_status_codes(self):
        b      = CloudFront__Origin__Failover__Builder(
            primary_origin_id  = 'p',
            fallback_origin_id = 'f',
        )
        result = b.build(status_codes=[503, 504])
        codes  = result['Items'][0]['FailoverCriteria']['StatusCodes']['Items']
        assert codes == [503, 504]
        assert result['Items'][0]['FailoverCriteria']['StatusCodes']['Quantity'] == 2
