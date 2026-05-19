# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Logs
# CLI tests for `sg aws logs` via Typer CliRunner. No mocks. No patches —
# the in-memory client is injected through ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time

import pytest
from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.logs.cli.Cli__Logs import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory import Logs__AWS__Client__In_Memory

runner = CliRunner()

_MUTATION_ENV = 'SG_AWS__LOGS__ALLOW_MUTATIONS'
_NOW          = int(time.time() * 1000)


def _obj(client):
    return {'logs_client': client}


class Test__Cli__Logs__Groups__List:

    def test_1__groups_list_empty(self):
        client = Logs__AWS__Client__In_Memory()
        result = runner.invoke(app, ['groups', 'list'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'No log groups found' in result.output

    def test_2__groups_list_json(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a', retention_days=7,  stored_bytes=1024)
        client.seed_group('/aws/ecs/svc',     retention_days=30, stored_bytes=2048)
        result = runner.invoke(app, ['groups', 'list', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data  = json.loads(result.output)
        names = sorted(g['name'] for g in data)
        assert names == ['/aws/ecs/svc', '/aws/lambda/fn-a']

    def test_3__groups_list_table_shows_name(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-x', retention_days=14)
        result = runner.invoke(app, ['groups', 'list'], obj=_obj(client))
        assert result.exit_code == 0
        assert '/aws/lambda/fn-x' in result.output

    def test_4__groups_list_table_shows_infinity_symbol(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/no-retention', retention_days=0)
        result = runner.invoke(app, ['groups', 'list'], obj=_obj(client))
        assert result.exit_code == 0
        assert '∞' in result.output

    def test_5__groups_list_prefix_filter_json(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a')
        client.seed_group('/aws/ecs/svc')
        result = runner.invoke(app, ['groups', 'list', '--prefix', '/aws/lambda', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['name'] == '/aws/lambda/fn-a'

    def test_6__groups_list_json_retention_field(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-b', retention_days=30)
        result = runner.invoke(app, ['groups', 'list', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]['retention_days'] == 30


class Test__Cli__Logs__Group__Describe:

    def test_7__group_describe_found_json(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a', retention_days=7, stored_bytes=512)
        result = runner.invoke(app, ['group', 'describe', '/aws/lambda/fn-a', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['name']           == '/aws/lambda/fn-a'
        assert data['retention_days'] == 7
        assert data['stored_bytes']   == 512

    def test_8__group_describe_not_found(self):
        client = Logs__AWS__Client__In_Memory()
        result = runner.invoke(app, ['group', 'describe', '/no-such-group'],
                               obj=_obj(client))
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_9__group_describe_table_shows_infinity(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/no-retention', retention_days=0)
        result = runner.invoke(app, ['group', 'describe', '/no-retention'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert '∞' in result.output

    def test_10__group_describe_table_shows_name(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/ecs/my-svc', retention_days=14)
        result = runner.invoke(app, ['group', 'describe', '/aws/ecs/my-svc'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert '/aws/ecs/my-svc' in result.output


class Test__Cli__Logs__Group__Create:

    def test_11__group_create_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['group', 'create', '/my/group', '--yes'])
        assert result.exit_code == 1
        assert _MUTATION_ENV in result.output

    def test_12__group_create_with_gate(self, monkeypatch):
        client = Logs__AWS__Client__In_Memory()
        monkeypatch.setenv(_MUTATION_ENV, '1')
        result = runner.invoke(app, ['group', 'create', '/my/new-group', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Created' in result.output
        assert client.describe_log_group('/my/new-group') is not None

    def test_13__group_create_already_exists_prints_skipped(self, monkeypatch):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/my/existing')
        monkeypatch.setenv(_MUTATION_ENV, '1')
        result = runner.invoke(app, ['group', 'create', '/my/existing', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Already exists' in result.output

    def test_14__group_create_with_retention_option(self, monkeypatch):
        client = Logs__AWS__Client__In_Memory()
        monkeypatch.setenv(_MUTATION_ENV, '1')
        result = runner.invoke(app, ['group', 'create', '/my/group', '--retention', '30', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        g = client.describe_log_group('/my/group')
        assert g.retention_days == 30


class Test__Cli__Logs__Group__Delete:

    def test_15__group_delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv(_MUTATION_ENV, raising=False)
        result = runner.invoke(app, ['group', 'delete', '/my/group', '--yes'])
        assert result.exit_code == 1
        assert _MUTATION_ENV in result.output

    def test_16__group_delete_with_gate(self, monkeypatch):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/my/group')
        monkeypatch.setenv(_MUTATION_ENV, '1')
        result = runner.invoke(app, ['group', 'delete', '/my/group', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert client.describe_log_group('/my/group') is None

    def test_17__group_delete_not_found_prints_skipped(self, monkeypatch):
        client = Logs__AWS__Client__In_Memory()
        monkeypatch.setenv(_MUTATION_ENV, '1')
        result = runner.invoke(app, ['group', 'delete', '/no-such-group', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Not found' in result.output


class Test__Cli__Logs__Tail:

    def test_18__tail_empty_group(self):
        client = Logs__AWS__Client__In_Memory()
        result = runner.invoke(app, ['tail', '/my/group'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'No log events found' in result.output

    def test_19__tail_shows_stream_and_message(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'app/server', 'hello world', _NOW - 100)
        result = runner.invoke(app, ['tail', '/my/group'], obj=_obj(client))
        assert result.exit_code == 0
        assert '[app/server]' in result.output
        assert 'hello world' in result.output

    def test_20__tail_multiple_events(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'stream/a', 'first',  _NOW - 200)
        client.seed_event('/my/group', 'stream/b', 'second', _NOW - 100)
        result = runner.invoke(app, ['tail', '/my/group'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'first'  in result.output
        assert 'second' in result.output

    def test_21__tail_with_stream_option(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'app/server', 'msg-a', _NOW - 100)
        client.seed_event('/my/group', 'bg/worker',  'msg-b', _NOW - 100)
        result = runner.invoke(app, ['tail', '/my/group', '--stream', 'app/'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'msg-a' in result.output
        assert 'msg-b' not in result.output

    def test_22__tail_since_option(self):
        client = Logs__AWS__Client__In_Memory()
        # event older than 5 minutes should not appear with --since 5
        client.seed_event('/my/group', 'stream/0', 'old-msg', _NOW - 700_000)
        client.seed_event('/my/group', 'stream/0', 'new-msg', _NOW - 100)
        result = runner.invoke(app, ['tail', '/my/group', '--since', '5'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'new-msg' in result.output
        assert 'old-msg' not in result.output
