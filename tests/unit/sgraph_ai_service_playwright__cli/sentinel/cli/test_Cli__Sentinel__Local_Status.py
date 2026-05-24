# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for `sg sentinel local status` (readiness view)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Local import app as local_app

runner = CliRunner()


def _env(d: str) -> dict:
    e = dict(os.environ)
    e['SG_SENTINEL__LOCAL_SINK_DIR'] = d
    return e


class TestStatus:
    def test_status_json_reports_readiness_fields(self):
        with tempfile.TemporaryDirectory() as d:
            r = runner.invoke(local_app, ['status', '--json'], env=_env(d))
            assert r.exit_code == 0
            info = json.loads(r.output)
            for key in ('node_available', 'docker_available', 'container_running', 'sink_dir', 'records', 'blocks'):
                assert key in info
            assert info['sink_dir'] == d
            assert info['records'] == 0

    def test_status_table_renders(self):
        with tempfile.TemporaryDirectory() as d:
            r = runner.invoke(local_app, ['status'], env=_env(d))
            assert r.exit_code == 0
            assert 'local stack' in r.output and 'CF-env container' in r.output
