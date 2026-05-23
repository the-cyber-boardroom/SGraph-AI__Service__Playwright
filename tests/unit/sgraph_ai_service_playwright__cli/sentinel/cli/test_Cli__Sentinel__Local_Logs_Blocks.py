# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for `sg sentinel local | logs | blocks` (Target B, via the CLI)
# Drives `local hit` over a temp sink (SG_SENTINEL__LOCAL_SINK_DIR), then asserts
# logs/blocks read it back. node-gated; the sink env override keeps $HOME clean.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile

from unittest      import skipUnless
from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Local            import app as local_app
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Logs             import app as logs_app
from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel__Blocks           import app as blocks_app
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source import node_available

runner = CliRunner()


def _env(d: str) -> dict:
    e = dict(os.environ)
    e['SG_SENTINEL__LOCAL_SINK_DIR'] = d
    return e


@skipUnless(node_available(), 'node not available')
class TestLocalHitThenRead:
    def test_hit_blocks_and_logs_and_blocks_surface_it(self):
        with tempfile.TemporaryDirectory() as d:
            env = _env(d)
            r1 = runner.invoke(local_app, ['hit', 'GET', '/etc/passwd', '--ip', '185.10.10.10', '--json'], env=env)
            assert r1.exit_code == 0
            signal = json.loads(r1.output)['signal']
            assert signal['verdict'] == 'block' and signal['rule_id'] == '0012'

            r2 = runner.invoke(logs_app, ['ls', '--json'], env=env)
            assert r2.exit_code == 0
            assert len(json.loads(r2.output)) == 1

            r3 = runner.invoke(blocks_app, ['list', '--json'], env=env)
            assert r3.exit_code == 0
            blocks = json.loads(r3.output)
            assert len(blocks) == 1
            assert blocks[0]['reason'] == 'path never valid'

    def test_trace_and_why_find_the_record(self):
        with tempfile.TemporaryDirectory() as d:
            env = _env(d)
            r1 = runner.invoke(local_app, ['hit', 'GET', '/etc/passwd', '--ip', '185.10.10.10', '--json'], env=env)
            request_id = json.loads(r1.output)['signal']['request_id']

            r2 = runner.invoke(logs_app, ['trace', request_id, '--json'], env=env)
            assert r2.exit_code == 0
            assert json.loads(r2.output)['request_id'] == request_id

            r3 = runner.invoke(blocks_app, ['why', '185.10.10.10', '--json'], env=env)   # raw ip → hashed match
            assert r3.exit_code == 0
            assert len(json.loads(r3.output)) == 1

    def test_benign_hit_passes_and_records_no_block(self):
        with tempfile.TemporaryDirectory() as d:
            env = _env(d)
            r1 = runner.invoke(local_app, ['hit', 'GET', '/index.html', '--ip', '198.51.100.2', '--json'], env=env)
            assert json.loads(r1.output)['enforcement']['pass_to_origin'] is True
            r2 = runner.invoke(blocks_app, ['list', '--json'], env=env)
            assert json.loads(r2.output) == []
