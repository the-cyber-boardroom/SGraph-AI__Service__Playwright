# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__User_Journey (`sg user-journey` status / scale / stop)
# CliRunner against a canned Conductor__Client injected via _client_factory (no HTTP,
# no mocks). Skips on 3.11 (typer absent), same gating as the rest of the CLI suite.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest import TestCase, skipUnless

try:
    from typer.testing import CliRunner
    _HAS_TYPER = True
except Exception:
    _HAS_TYPER = False

if _HAS_TYPER:
    from sg_compute_specs.user_journey.cli.Cli__User_Journey import app as uj_app
    import sg_compute_specs.user_journey.cli.Cli__User_Journey as uj_mod
    from sg_compute_specs.user_journey.core.clients.Conductor__Client               import Conductor__Client
    from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State   import Enum__Suite__Run__State
    from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status
    from sg_compute_specs.user_journey.core.schemas.enums.Enum__Journey__Run__Status import Enum__Journey__Run__Status
    from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition import Schema__Journey__Definition
    from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Result     import Schema__Journey__Result

    class _Canned_Runner:                                                            # stands in for Journey__Local__Runner (no browser)
        def run_file(self, path, run_id=None):
            journey            = Schema__Journey__Definition()
            journey.journey_id = 'checkout'
            result             = Schema__Journey__Result(status=Enum__Journey__Run__Status.PASSED)
            flows              = [{'method': 'GET', 'status': 200, 'url': 'https://shop.test/'}]
            return (journey, run_id or 'local-abc123', result, flows)

    class _Canned_Conductor(Conductor__Client):
        def get_suite(self, suite_run_id):
            status          = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
            status.suite_id = 'checkout-load'
            status.counts.passed = 2
            return status

        def scale_suite(self, suite_run_id, count, concurrency):
            return Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)

        def stop_suite(self, suite_run_id):
            return Schema__Suite__Run__Status(state=Enum__Suite__Run__State.STOPPED)

        def get_flows(self, suite_run_id):
            return [{'method': 'GET', 'status': 200, 'url': 'https://shop.test/'}]


@skipUnless(_HAS_TYPER, 'typer not installed (Python <3.12 in this env)')
class test_Cli__User_Journey(TestCase):

    def setUp(self):
        uj_mod._client_factory = lambda: _Canned_Conductor()
        self.runner = CliRunner()

    def tearDown(self):
        uj_mod._client_factory = None
        uj_mod._runner_factory = None

    def test_status__renders_cockpit(self):
        result = self.runner.invoke(uj_app, ['status', 'r1'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'checkout-load' in result.output

    def test_status__json(self):
        result = self.runner.invoke(uj_app, ['status', 'r1', '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        assert json.loads(result.output)['suite_id'] == 'checkout-load'

    def test_scale__confirms(self):
        result = self.runner.invoke(uj_app, ['scale', 'r1', '10', '4'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'scaled' in result.output and 'count=10' in result.output

    def test_stop__confirms(self):
        result = self.runner.invoke(uj_app, ['stop', 'r1'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'stopped' in result.output

    def test_flows__lists_requests(self):
        result = self.runner.invoke(uj_app, ['flows', 'r1'], catch_exceptions=False)
        assert result.exit_code == 0
        assert '1 flow' in result.output
        assert 'GET' in result.output and 'https://shop.test/' in result.output

    def test_flows__json(self):
        result = self.runner.invoke(uj_app, ['flows', 'r1', '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        assert json.loads(result.output)[0]['status'] == 200

    def test_run_local__prints_result_and_flows(self):
        uj_mod._runner_factory = lambda: _Canned_Runner()
        result = self.runner.invoke(uj_app, ['run-local', 'checkout.json'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'checkout' in result.output
        assert 'passed'   in result.output.lower()
        assert '1 flow'   in result.output
        assert 'https://shop.test/' in result.output

    def test_run_local__json(self):
        uj_mod._runner_factory = lambda: _Canned_Runner()
        result = self.runner.invoke(uj_app, ['run-local', 'checkout.json', '--run-id', 'r9', '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload['run_id'] == 'r9'
        assert payload['flows'][0]['status'] == 200

    def test_no_args_shows_help(self):
        result = self.runner.invoke(uj_app, [])
        assert result.exit_code != 0 or 'status' in result.output
