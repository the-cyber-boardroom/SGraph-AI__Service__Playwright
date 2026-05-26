# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Screen pilot test
# Drives the real Textual app via App.run_test() — no mocks, no real terminal.
# Skips cleanly when Textual is not installed (operator tooling, not runtime).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import IsolatedAsyncioTestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    from sg_compute_specs.vscode.tui.screens.Vscode__TUI__Screen__Stacks import Vscode__TUI__Screen__Stacks
    from sg_compute_specs.vscode.tui.source.Vscode__TUI__Data_Source     import Vscode__TUI__Data_Source
    from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot
    from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Stack    import Schema__Vscode__TUI__Stack
    TEXTUAL = True
except Exception:
    TEXTUAL = False


if TEXTUAL:
    class Fake_Source(Vscode__TUI__Data_Source):
        def snapshot(self):
            row = Schema__Vscode__TUI__Stack(stack_name='brave-fermi', state='running',
                                             distribution='code-server', vscode_url='http://localhost:8443')
            return Schema__Vscode__TUI__Snapshot(region='eu-west-2', captured_at=1700000000,
                                                 can_act=True, total=1, stacks=[row])


@skipUnless(TEXTUAL, 'textual not installed')
class test_Vscode__TUI__Screen__Stacks(IsolatedAsyncioTestCase):

    async def test_body_renders_stack(self):
        from textual.widgets import Static
        app = Vscode__TUI__Screen__Stacks(source=Fake_Source())
        async with app.run_test() as pilot:                                          # noqa: F841
            text = str(app.query_one('#body', Static).content)                       # the markup populate() set
            assert 'brave-fermi'           in text
            assert 'http://localhost:8443' in text
            assert len(app.debug_log.events) > 0                                     # populate → source.snapshot logged an event
