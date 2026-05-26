# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: pure render + ASCII card tests (no Textual)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot
from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Stack    import Schema__Vscode__TUI__Stack
from sg_compute_specs.vscode.tui.service.Vscode__TUI__Card             import Vscode__TUI__Card
from sg_compute_specs.vscode.tui.service.Vscode__TUI__Render           import Vscode__TUI__Render


def _snapshot(stacks=None):
    return Schema__Vscode__TUI__Snapshot(region='eu-west-2', captured_at=1700000000, can_act=True,
                                         total=len(stacks or []), stacks=stacks or [])


def _row(**kw):
    base = dict(stack_name='brave-fermi', instance_id='i-1', state='running',
                distribution='code-server', ingress='ssm-forward', region='eu-west-2',
                vscode_url='http://localhost:8443')
    base.update(kw)
    return Schema__Vscode__TUI__Stack(**base)


class test_Vscode__TUI__Render(TestCase):

    def test_empty(self):
        out = Vscode__TUI__Render().stacks_markup(_snapshot())
        assert 'sg vscode create' in out

    def test_with_stack(self):
        out = Vscode__TUI__Render().stacks_markup(_snapshot([_row()]))
        assert 'brave-fermi'           in out
        assert 'code-server'           in out
        assert 'http://localhost:8443' in out
        assert '[green]running'        in out                  # state colourised

    def test_escapes_markup_in_names(self):
        out = Vscode__TUI__Render().stacks_markup(_snapshot([_row(stack_name='a[b]c')]))
        assert r'a\[b]c' in out                                # Rich markup neutralised


class test_Vscode__TUI__Card(TestCase):

    def test_card_lists_stacks_and_native_commands(self):
        out = Vscode__TUI__Card().render(_snapshot([_row()]))
        assert 'VS Code stacks'           in out
        assert 'brave-fermi'              in out
        assert 'sg vscode forward <name>' in out               # native-command footer (rule: no TUI-only)
        assert '[' not in out                                  # plain ASCII — no Rich markup
