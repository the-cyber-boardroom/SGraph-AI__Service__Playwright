# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui/tui_api: Vscode__Tui_Api__Provider tests
# No mocks — a Fake source (Data_Source subclass) returns a canned snapshot and
# records deletes. Skips if the tool_api framework is unavailable.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    from sg_compute_specs.vscode.tui.source.Vscode__TUI__Data_Source       import Vscode__TUI__Data_Source
    from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot
    from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Stack    import Schema__Vscode__TUI__Stack
    from sg_compute_specs.vscode.tui.tui_api.Vscode__Tui_Api__Provider     import Vscode__Tui_Api__Provider
    IMPORTABLE = True
except Exception:
    IMPORTABLE = False


if IMPORTABLE:
    class Fake_Source(Vscode__TUI__Data_Source):
        deleted : list = None

        def snapshot(self):
            row = Schema__Vscode__TUI__Stack(stack_name='brave-fermi', state='running',
                                             distribution='code-server', vscode_url='http://localhost:8443')
            return Schema__Vscode__TUI__Snapshot(region='eu-west-2', captured_at=1700000000,
                                                 can_act=True, total=1, stacks=[row])

        def can_act(self):
            return True

        def delete(self, stack_name: str) -> bool:
            if self.deleted is None:
                self.deleted = []
            self.deleted.append(stack_name)
            return True


@skipUnless(IMPORTABLE, 'tui tool_api framework not importable')
class test_Vscode__Tui_Api__Provider(TestCase):

    def provider(self):
        return Vscode__Tui_Api__Provider(source=Fake_Source())

    def test_manifest_actions(self):
        manifest = self.provider().manifest()
        names    = {str(a.name) for a in manifest.actions}
        assert names == {'status', 'list', 'delete'}
        assert str(manifest.slug) == 'vscode'

    def test_state(self):
        st = self.provider().state()
        assert st['can_act']     is True
        assert st['region']      == 'eu-west-2'
        assert st['stack_count'] == 1

    def test_dispatch_status_and_list(self):
        p = self.provider()
        status = p.dispatch('status', {})
        assert status.ok is True
        assert status.data['result']['total'] == 1
        listing = p.dispatch('list', {})
        assert listing.ok is True
        assert len(listing.data['result']['stacks']) == 1

    def test_dispatch_delete(self):
        p   = self.provider()
        res = p.dispatch('delete', {'stack_name': 'brave-fermi'})
        assert res.ok is True
        assert res.data['result']['deleted'] is True
        assert p.source.deleted == ['brave-fermi']

    def test_dispatch_delete_requires_name(self):
        res = self.provider().dispatch('delete', {})
        assert res.ok is False
        assert 'stack_name is required' in res.error

    def test_dispatch_unknown_action(self):
        res = self.provider().dispatch('nope', {})
        assert res.ok is False
        assert 'unknown action' in res.error
