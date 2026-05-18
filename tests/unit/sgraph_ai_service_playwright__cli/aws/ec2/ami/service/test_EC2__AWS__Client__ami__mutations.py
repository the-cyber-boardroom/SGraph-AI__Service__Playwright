# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client AMI/snapshot mutation methods
# Direct client tests for deregister_image and delete_snapshot (success,
# missing, in-use). In-memory backed; no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from botocore.exceptions import ClientError

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__deregister_image:

    def test_1__success_returns_true(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self')
        result = client.deregister_image('ami-aaaaaaaa')
        assert result is True
        # confirm gone
        assert client.describe_ami('ami-aaaaaaaa') is None

    def test_2__missing_returns_false(self):
        client = EC2__AWS__Client__In_Memory()
        result = client.deregister_image('ami-deadbeef')
        assert result is False


class Test__EC2__AWS__Client__delete_snapshot:

    def test_1__success_returns_true(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_snapshot(snapshot_id='snap-aaaaaaaa', owner='self')
        result = client.delete_snapshot('snap-aaaaaaaa')
        assert result is True
        assert len(client.list_snapshots(owner='self')) == 0

    def test_2__missing_returns_false(self):
        client = EC2__AWS__Client__In_Memory()
        result = client.delete_snapshot('snap-deadbeef')
        assert result is False

    def test_3__in_use_re_raises(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_snapshot(snapshot_id='snap-aaaaaaaa', owner='self',
                             in_use=True)
        with pytest.raises(ClientError) as exc:
            client.delete_snapshot('snap-aaaaaaaa')
        assert exc.value.response['Error']['Code'] == 'InvalidSnapshot.InUse'
        # still present
        assert len(client.list_snapshots(owner='self')) == 1
