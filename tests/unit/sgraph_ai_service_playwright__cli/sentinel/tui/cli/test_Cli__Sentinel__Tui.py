# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for `sg sentinel tui` (--json + no-TTY paths, via the source seam)
# CliRunner output is non-TTY, so these exercise the plain/JSON fallbacks (no Textual
# app is launched). An in-memory source is injected via _source_factory (no AWS).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

import sgraph_ai_service_playwright__cli.sentinel.tui.cli.Cli__Sentinel__Tui as tui_cli
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink  import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.cli.Cli__Sentinel__Tui            import app
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source      import Sentinel__TUI__Source

runner = CliRunner()


def _install_source(records):
    sink = InMemory__Log__Sink()
    for r in records:
        sink.write(r)
    tui_cli._source_factory = lambda: Sentinel__TUI__Source(log_sink=sink)


def teardown_function(_):
    tui_cli._source_factory = None


def _block(request_id='sn-1'):
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at='2026-05-23T14:30:00Z', method='GET',
                                        path='/etc/passwd', host='h', source_ip='abc', verdict='block',
                                        reason='path never valid', rule_id='0012', http_status=403, enforced=True)


class TestRules:
    def test_rules_json(self):
        _install_source([])
        r = runner.invoke(app, ['rules', '--json'])
        assert r.exit_code == 0
        assert len(json.loads(r.output)) == 6

    def test_rules_plain_when_not_tty(self):
        _install_source([])
        r = runner.invoke(app, ['rules'])                                            # CliRunner stdout is not a TTY → plain
        assert r.exit_code == 0
        assert '0012' in r.output and '[' not in r.output


class TestLogsBlocks:
    def test_logs_json_lists_records(self):
        _install_source([_block('sn-a'), _block('sn-b')])
        r = runner.invoke(app, ['logs', '--json'])
        assert r.exit_code == 0 and len(json.loads(r.output)) == 2

    def test_blocks_json_aggregates(self):
        _install_source([_block('sn-a'), _block('sn-b')])
        r = runner.invoke(app, ['blocks', '--json'])
        assert r.exit_code == 0
        groups = json.loads(r.output)
        assert groups[0]['rule_id'] == '0012' and groups[0]['count'] == 2

    def test_blocks_plain_when_not_tty(self):
        _install_source([_block()])
        r = runner.invoke(app, ['blocks'])
        assert r.exit_code == 0 and 'path never valid' in r.output


class TestStatus:
    def test_status_json(self):
        _install_source([_block()])
        r = runner.invoke(app, ['status', '--json'])
        assert r.exit_code == 0
        info = json.loads(r.output)
        assert info['rule_count'] == 6 and info['block_count'] == 1
