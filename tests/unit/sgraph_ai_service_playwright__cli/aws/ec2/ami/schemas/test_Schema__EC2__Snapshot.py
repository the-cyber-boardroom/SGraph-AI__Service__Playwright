# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__EC2__Snapshot
# Short round-trip + defaults for the EBS snapshot schema.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id import Safe_Str__EC2__Snapshot_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Volume_Id   import Safe_Str__EC2__Volume_Id
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Snapshot          import Schema__EC2__Snapshot


class Test__Schema__EC2__Snapshot:

    def test_1__defaults_are_empty(self):
        snap = Schema__EC2__Snapshot()
        assert str(snap.snapshot_id)     == ''
        assert str(snap.volume_id)       == ''
        assert int(snap.volume_size_gib) == 0
        assert str(snap.description)     == ''
        assert str(snap.state)           == ''
        assert str(snap.started_at)      == ''
        assert str(snap.owner_id)        == ''

    def test_2__fields_accept_primitives(self):
        snap = Schema__EC2__Snapshot(
            snapshot_id     = Safe_Str__EC2__Snapshot_Id('snap-12345678'),
            volume_id       = Safe_Str__EC2__Volume_Id('vol-12345678'),
            volume_size_gib = 16,
            description     = 'nightly backup',
            state           = 'completed',
            started_at      = '2026-04-01T00:00:00.000Z',
            owner_id        = '123456789012',
        )
        assert str(snap.snapshot_id)     == 'snap-12345678'
        assert str(snap.volume_id)       == 'vol-12345678'
        assert int(snap.volume_size_gib) == 16
        assert str(snap.state)           == 'completed'
