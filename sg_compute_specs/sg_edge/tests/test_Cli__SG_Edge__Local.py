# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: tests for the `sg edge local` CLI
# CliRunner tests driving the local sub-app against an isolated temp state dir
# (injected via the module-level _stack_factory — no mocks). Covers the full
# operator flow (setup → register → request → list → check → teardown), the --json
# contracts, the ASCII check render, and the use-case runner. Skips on 3.11
# (typer absent), same gating as the rest of the CLI suite.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import shutil
import tempfile
from unittest import TestCase, skipUnless

try:
    from typer.testing import CliRunner                                              # noqa: F401 — availability probe
    _HAS_TYPER = True
except Exception:
    _HAS_TYPER = False

if _HAS_TYPER:
    from sg_compute_specs.sg_edge.local.cli.Cli__SG_Edge__Local import app as local_app
    import sg_compute_specs.sg_edge.local.cli.Cli__SG_Edge__Local as local_mod
    from sg_compute_specs.sg_edge.local.Local__Edge__Stack       import Local__Edge__Stack


@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__SG_Edge__Local(TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-cli-test-')
        local_mod._stack_factory = lambda parent: Local__Edge__Stack(
            parent=parent or 'edge.sg-labs.local', state_dir=self.dir)
        self.runner = CliRunner()

    def tearDown(self):
        local_mod._stack_factory = None
        shutil.rmtree(self.dir, ignore_errors=True)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def test_setup__exits_0(self):
        result = self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'deployed' in result.output

    # ── dry-run previews (the native home for the TUI Control Center previews) ──

    def test_register_dry_run__previews_without_mutating(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['register', 'zoe', '--dry-run'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'dry-run' in result.output and 'zoe' in result.output
        listed = self.runner.invoke(local_app, ['list'], catch_exceptions=False)     # not actually registered
        assert 'zoe' not in listed.output

    def test_teardown_dry_run__previews_without_deleting(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['teardown', '--dry-run'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'dry-run' in result.output
        status = self.runner.invoke(local_app, ['status'], catch_exceptions=False)   # still deployed
        assert 'deployed=True' in status.output

    def test_register_then_request__welcome(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'alice'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['request', 'alice'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'welcome' in result.output
        assert '200'     in result.output

    def test_request__json(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'alice'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['request', 'alice', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert data['status_code'] == 200
        assert data['kind']        == 'welcome'
        assert 'Welcome to the alice vault' in data['body']

    def test_request_unknown__not_recognised(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['request', 'ghost', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert data['status_code'] == 404
        assert data['kind']        == 'not_recognised'

    def test_register_no_backend__dormant(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'bob', '--no-backend'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['request', 'bob', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert data['kind'] == 'dormant'

    def test_unregister__exits_0_then_404(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'carol'], catch_exceptions=False)
        un = self.runner.invoke(local_app, ['unregister', 'carol'], catch_exceptions=False)
        assert un.exit_code == 0
        result = self.runner.invoke(local_app, ['request', 'carol', '--json'], catch_exceptions=False)
        assert json.loads(result.output)['kind'] == 'not_recognised'

    def test_unregister_absent__exits_1(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['unregister', 'nobody'])
        assert result.exit_code == 1

    def test_list__shows_registered(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'alice'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['list'], catch_exceptions=False)
        assert 'alice' in result.output

    def test_status__json(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['status', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert data['deployed'] is True
        assert data['wildcard'] is True

    def test_teardown__yes(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['teardown', '--yes'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'torn down' in result.output

    # ── check (ASCII art) ───────────────────────────────────────────────────────

    def test_check__renders_ascii_box(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        self.runner.invoke(local_app, ['register', 'alice'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['check'], catch_exceptions=False)
        assert result.exit_code == 0
        assert '┌' in result.output and '─' in result.output                         # box-drawing present
        assert 'SG/Edge' in result.output
        assert 'alice'   in result.output

    def test_check__not_deployed_exits_0(self):
        result = self.runner.invoke(local_app, ['check'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'not deployed' in result.output

    def test_check__json(self):
        self.runner.invoke(local_app, ['setup'], catch_exceptions=False)
        result = self.runner.invoke(local_app, ['check', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert data['deployed'] is True
        assert 'issues' in data

    # ── use-cases ─────────────────────────────────────────────────────────────

    def test_usecases__lists(self):
        result = self.runner.invoke(local_app, ['usecases'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'UC-01' in result.output
        assert 'UC-06' in result.output

    def test_usecase_single__passes(self):
        result = self.runner.invoke(local_app, ['usecase', 'UC-02'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'PASS' in result.output

    def test_usecase_all__passes(self):
        result = self.runner.invoke(local_app, ['usecase', 'all'], catch_exceptions=False)
        assert result.exit_code == 0
        assert '6/6 use-case(s) passed' in result.output

    def test_usecase_unknown__exits_1(self):
        result = self.runner.invoke(local_app, ['usecase', 'UC-99'])
        assert result.exit_code == 1

    def test_usecase_all__json(self):
        result = self.runner.invoke(local_app, ['usecase', 'all', '--json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert len(data) == 6
        assert all(uc['passed'] for uc in data)
