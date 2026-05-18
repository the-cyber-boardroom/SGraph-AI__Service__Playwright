# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client.list_snapshots
# In-memory backed; covers owner=self and owner=all paths.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_snapshots:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        snaps  = client.list_snapshots()
        assert len(snaps) == 0

    def test_2__owner_self_returns_self_only(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_snapshot(snapshot_id='snap-aaaaaaaa', owner='self',
                             volume_id='vol-aaaaaaaa', size_gib=8)
        client.seed_snapshot(snapshot_id='snap-bbbbbbbb', owner='amazon',
                             volume_id='vol-bbbbbbbb', size_gib=32)
        snaps = client.list_snapshots(owner='self')
        ids   = {str(s.snapshot_id) for s in snaps}
        assert ids == {'snap-aaaaaaaa'}

    def test_3__owner_all_returns_all(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_snapshot(snapshot_id='snap-aaaaaaaa', owner='self',
                             volume_id='vol-aaaaaaaa', size_gib=8)
        client.seed_snapshot(snapshot_id='snap-bbbbbbbb', owner='amazon',
                             volume_id='vol-bbbbbbbb', size_gib=32)
        snaps = client.list_snapshots(owner='all')
        assert len(snaps) == 2

    def test_4__fields_round_trip(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_snapshot(snapshot_id='snap-aaaaaaaa', owner='self',
                             volume_id='vol-aaaaaaaa', size_gib=16,
                             description='nightly')
        snaps = client.list_snapshots(owner='self')
        assert len(snaps) == 1
        s = snaps[0]
        assert str(s.snapshot_id)     == 'snap-aaaaaaaa'
        assert str(s.volume_id)       == 'vol-aaaaaaaa'
        assert int(s.volume_size_gib) == 16
        assert str(s.description)     == 'nightly'
        assert str(s.state)           == 'completed'
