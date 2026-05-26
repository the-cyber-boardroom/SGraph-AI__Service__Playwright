# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Snapshot__Builder tests (pure)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.schemas.Schema__Vscode__Info             import Schema__Vscode__Info
from sg_compute_specs.vscode.schemas.Schema__Vscode__List             import Schema__Vscode__List
from sg_compute_specs.vscode.tui.service.Vscode__TUI__Snapshot__Builder import Vscode__TUI__Snapshot__Builder


class test_Vscode__TUI__Snapshot__Builder(TestCase):

    def _listing(self):
        info = Schema__Vscode__Info(stack_name='brave-fermi', instance_id='i-1', state='running',
                                    distribution='code-server', ingress='ssm-forward', region='eu-west-2',
                                    vscode_url='http://localhost:8443', ssm_forward='aws ssm ...', spot=True)
        return Schema__Vscode__List(region='eu-west-2', stacks=[info], total=1)

    def test_build_maps_fields(self):
        snap = Vscode__TUI__Snapshot__Builder().build(self._listing(), can_act=True)
        assert snap.region   == 'eu-west-2'
        assert snap.total    == 1
        assert snap.can_act  is True
        assert snap.captured_at > 0
        row = snap.stacks[0]
        assert row.stack_name   == 'brave-fermi'
        assert row.state        == 'running'
        assert row.distribution == 'code-server'
        assert row.vscode_url   == 'http://localhost:8443'
        assert row.spot         is True

    def test_build_empty(self):
        snap = Vscode__TUI__Snapshot__Builder().build(Schema__Vscode__List(region='eu-west-2'), can_act=False)
        assert snap.total   == 0
        assert snap.stacks  == []
        assert snap.can_act is False
