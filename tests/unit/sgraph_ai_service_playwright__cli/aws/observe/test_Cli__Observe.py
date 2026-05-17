# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Observe
# 8 CLI tests exercising sources, tail, query, stats, agent-trace via CliRunner.
# No mocks. No patches. Registry injected via module-level _registry seam.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import pytest
from typer.testing import CliRunner

import sgraph_ai_service_playwright__cli.aws.observe.cli.Cli__Observe as cli_module
from sgraph_ai_service_playwright__cli.aws.observe.cli.Cli__Observe import app
from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry  import Source__Registry
from tests.unit.sgraph_ai_service_playwright__cli.aws.observe._Stub__Source__Adapter import _Stub__Source__Adapter

runner = CliRunner()


def _make_registry() -> Source__Registry:
    reg     = Source__Registry()
    adapter = _Stub__Source__Adapter()
    adapter.connect()
    adapter.add_stream('my-stream')
    adapter.add_event('2026-05-17T10:00:00Z', 'hello world',   stream='my-stream')
    adapter.add_event('2026-05-17T10:01:00Z', 'error occurred', stream='my-stream')
    reg.register('stub', adapter)
    return reg


class Test__Cli__Observe:

    def setup_method(self):
        cli_module._registry = _make_registry()

    def teardown_method(self):
        cli_module._registry = None

    def test_1__sources_plain(self):
        result = runner.invoke(app, ['sources'])
        assert result.exit_code == 0
        assert 'stub' in result.output

    def test_2__sources_json(self):
        result = runner.invoke(app, ['sources', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['name'] == 'stub'

    def test_3__tail_json(self):
        result = runner.invoke(app, ['tail', '--source', 'stub', '--stream', 'my-stream', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_4__tail_missing_source_exits_1(self):
        result = runner.invoke(app, ['tail', '--source', 'nonexistent', '--json'])
        assert result.exit_code == 1

    def test_5__query_json(self):
        result = runner.invoke(app, ['query', 'hello', '--source', 'stub', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert any('hello' in ev['message'] for ev in data)

    def test_6__stats_json(self):
        result = runner.invoke(app, [
            'stats', '--source', 'stub', '--stream', 'my-stream', '--by', 'count', '--json',
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['aggregation'] == 'count'
        assert 'total' in data

    def test_7__agent_trace_json(self):
        result = runner.invoke(app, ['agent-trace', 'sess-test-42', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['session_id'] == 'sess-test-42'
        assert 'total_events' in data

    def test_8__sources_empty_registry(self):
        cli_module._registry = Source__Registry()                      # empty registry
        result = runner.invoke(app, ['sources'])
        assert result.exit_code == 0
        assert 'No sources' in result.output
