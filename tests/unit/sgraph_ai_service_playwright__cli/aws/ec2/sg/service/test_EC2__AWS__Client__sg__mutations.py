# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client SG mutation methods
# Direct client tests for delete_security_group (success, missing → False,
# DependencyViolation re-raises when an ENI is still attached). In-memory
# backed; no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from botocore.exceptions import ClientError

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__delete_security_group:

    def test_1__success_returns_true(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        result = client.delete_security_group('sg-aaaaaaaa')
        assert result is True
        # confirm gone
        assert client.describe_security_group('sg-aaaaaaaa') is None

    def test_2__missing_returns_false(self):
        client = EC2__AWS__Client__In_Memory()
        result = client.delete_security_group('sg-deadbeef')
        assert result is False

    def test_3__dependency_violation_re_raises(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_network_interface(eni_id='eni-11111111',
                                       sg_ids=['sg-aaaaaaaa'],
                                       instance_id='i-12345678')
        with pytest.raises(ClientError) as exc:
            client.delete_security_group('sg-aaaaaaaa')
        assert exc.value.response['Error']['Code'] == 'DependencyViolation'
        # SG still present
        assert client.describe_security_group('sg-aaaaaaaa') is not None

    def test_4__by_name_resolves_then_deletes(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='by-name',
                                    vpc_id='vpc-aaaaaaaa')
        result = client.delete_security_group('by-name', vpc_id='vpc-aaaaaaaa')
        assert result is True
        assert client.describe_security_group('sg-aaaaaaaa') is None
