# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for CloudFront__AWS__Client Lambda@Edge association (Sentinel)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request  import Schema__CF__Create__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client__In_Memory import CloudFront__AWS__Client__In_Memory

_ARN = 'arn:aws:lambda:us-east-1:123456789012:function:sg-sentinel-l2:3'


def _client_with_dist():
    client = CloudFront__AWS__Client__In_Memory()
    resp   = client.create_distribution(Schema__CF__Create__Request(origin_domain=Safe_Str__CF__Domain_Name('example.com')))
    return client, str(resp.distribution_id)


class TestAssociate:
    def test_associate_then_read_back(self):
        client, dist_id = _client_with_dist()
        assert client.associate_lambda_edge(dist_id, _ARN, 'origin-request') is True
        assert client.get_lambda_edge_associations(dist_id, 'origin-request') == [_ARN]

    def test_associate_replaces_prior_for_same_event_type(self):
        client, dist_id = _client_with_dist()
        client.associate_lambda_edge(dist_id, _ARN, 'origin-request')
        client.associate_lambda_edge(dist_id, _ARN + 'x'.replace('x', '4'), 'origin-request')
        assert len(client.get_lambda_edge_associations(dist_id, 'origin-request')) == 1


class TestDisassociate:
    def test_disassociate_removes_it(self):
        client, dist_id = _client_with_dist()
        client.associate_lambda_edge(dist_id, _ARN, 'origin-request')
        assert client.disassociate_lambda_edge(dist_id, 'origin-request') is True
        assert client.get_lambda_edge_associations(dist_id, 'origin-request') == []
