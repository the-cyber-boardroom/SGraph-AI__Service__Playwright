# ═══════════════════════════════════════════════════════════════════════════════
# Tests — test_Cli__Vault_App__Fargate__Start
# CLI-level tests for task-level commands on `sg vault-app fargate`.
# Uses Typer CliRunner + in-memory clients injected via ctx.obj.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile

import pytest
from typer.testing import CliRunner

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Timings__Record import Schema__VAF__Timings__Record
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health  import Vault_App__Fargate__Health
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Timings__Store import Vault_App__Fargate__Timings__Store

from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory      import Logs__AWS__Client__In_Memory

runner   = CliRunner()
_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'


# ── helpers ───────────────────────────────────────────────────────────────────

def _healthy_http(url, headers):                                                  # stub that immediately returns 200 OK
    return 200, True


def _unhealthy_http(url, headers):                                                # stub that always returns failure
    return 0, False


def _default_fargate() -> Fargate__AWS__Client__In_Memory:
    fargate = Fargate__AWS__Client__In_Memory()
    fargate.seed_cluster_with_tags('test-cluster', {
        'Stack'                  : 'sg-vault-app-fargate',
        'VaultApp__Subnets'      : 'subnet-aaa',
        'VaultApp__SecurityGroup': 'sg-xxx',
        'VaultApp__LogGroup'     : '/ecs/vault-app',
        'VaultApp__EcrRepoName'  : 'sg-send-vault',
        'VaultApp__Region'       : 'us-east-1',
    })
    fargate.register_task_definition(
        name='vault-app', image='ecr.io/sg-send-vault:latest', cpu='512', memory='1024')
    return fargate


def _default_obj(fargate=None, health=None, timings_store=None, logs=None):
    return {
        'fargate_client': fargate      or _default_fargate(),
        'logs_client'   : logs         or Logs__AWS__Client__In_Memory(),
        'health'        : health       or Vault_App__Fargate__Health(_http_get=_healthy_http, timeout_seconds=1),
        'timings_store' : timings_store,                                          # None = default path (not used in start tests)
    }


def _fargate_with_running_task(slug: str = 'test-slug') -> Fargate__AWS__Client__In_Memory:
    fargate = _default_fargate()
    fargate.seed_task_with_tags('test-cluster', {'VaultApp__Slug': slug})
    return fargate


def _run(args, obj=None):
    return runner.invoke(fargate_app, args, obj=obj or _default_obj())


# ════════════════════════════════════════════════════════════════════════════════
# start
# ════════════════════════════════════════════════════════════════════════════════

class Test__Start:

    def test_1__start_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = _run(['start', '--yes'])
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__start_with_gate_json_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert 'slug' in data
        assert 'task_arn' in data

    def test_3__start_json_has_timings_block(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert 'timings' in data
        assert 'task_ready_ms' in data['timings']
        assert 'vault_ready_ms' in data['timings']
        assert 'total_ms' in data['timings']

    def test_4__start_json_has_phases_array(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data['phases'], list)
        assert len(data['phases']) > 0

    def test_5__start_json_ok_true_on_success(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['ok'] is True

    def test_6__start_json_cluster_name_matches(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['cluster_name'] == 'test-cluster'

    def test_7__start_json_custom_slug(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster',
                       '--slug', 'my-slug'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['slug'] == 'my-slug'

    def test_8__start_json_has_access_token_when_provided(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster',
                       '--access-token', 'sg_test_token'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['access_token'] == 'sg_test_token'

    def test_9__start_json_executed_at_present(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        result = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['executed_at'] != ''

    def test_10__start_auto_resolves_sole_cluster(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        # Only one cluster tagged — should auto-resolve without --cluster flag
        result = _run(['start', '--yes', '--json'],
                      obj=_default_obj())
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['cluster_name'] == 'test-cluster'

    def test_11__start_unhealthy_exits_nonzero(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        bad_health = Vault_App__Fargate__Health(_http_get=_unhealthy_http, timeout_seconds=0)
        obj        = _default_obj(health=bad_health)
        result     = _run(['start', '--yes', '--json', '--cluster', 'test-cluster'], obj=obj)
        assert result.exit_code != 0


# ════════════════════════════════════════════════════════════════════════════════
# stop
# ════════════════════════════════════════════════════════════════════════════════

class Test__Stop:

    def test_1__stop_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['stop', '--slug', 'my-vault', '--cluster', 'test-cluster', '--yes'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__stop_with_gate_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['stop', '--slug', 'my-vault', '--cluster', 'test-cluster', '--yes'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0, result.output
        assert 'my-vault' in result.output

    def test_3__stop_json_returns_slug_and_stopped_true(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['stop', '--slug', 'my-vault', '--cluster', 'test-cluster',
                        '--yes', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['slug'] == 'my-vault'
        assert data['stopped'] is True
        assert 'task_arn' in data

    def test_4__stop_no_running_task_exits_nonzero(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        # fargate with no running tasks — slug resolve will raise ValueError
        fargate = _default_fargate()
        result  = _run(['stop', '--slug', 'missing-vault', '--cluster', 'test-cluster',
                        '--yes', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code != 0

    def test_5__stop_auto_resolves_sole_running_task(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _fargate_with_running_task('solo-vault')
        result  = _run(['stop', '--cluster', 'test-cluster', '--yes', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['stopped'] is True


# ════════════════════════════════════════════════════════════════════════════════
# restart
# ════════════════════════════════════════════════════════════════════════════════

class Test__Restart:

    def test_1__restart_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['restart', '--slug', 'my-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__restart_with_gate_json_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['restart', '--slug', 'my-vault', '--cluster', 'test-cluster', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['slug'] == 'my-vault'

    def test_3__restart_json_has_ok_true(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _fargate_with_running_task('my-vault')
        result  = _run(['restart', '--slug', 'my-vault', '--cluster', 'test-cluster', '--json'],
                       obj=_default_obj(fargate=fargate))
        data = json.loads(result.output)
        assert data['ok'] is True


# ════════════════════════════════════════════════════════════════════════════════
# health
# ════════════════════════════════════════════════════════════════════════════════

class Test__Health:

    def test_1__health_healthy_task_prints_healthy(self):
        fargate = _fargate_with_running_task('healthy-vault')
        health  = Vault_App__Fargate__Health(_http_get=_healthy_http, timeout_seconds=1)
        result  = _run(['health', '--slug', 'healthy-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate, health=health))
        assert result.exit_code == 0, result.output
        assert 'healthy' in result.output

    def test_2__health_unhealthy_task_exits_nonzero(self):
        fargate = _fargate_with_running_task('sick-vault')
        health  = Vault_App__Fargate__Health(_http_get=_unhealthy_http, timeout_seconds=0)
        result  = _run(['health', '--slug', 'sick-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate, health=health))
        assert result.exit_code != 0
        assert 'unhealthy' in result.output

    def test_3__health_missing_slug_exits_nonzero(self):
        fargate = _default_fargate()                                               # no tasks
        health  = Vault_App__Fargate__Health(_http_get=_healthy_http, timeout_seconds=1)
        result  = _run(['health', '--slug', 'no-such-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate, health=health))
        assert result.exit_code != 0


# ════════════════════════════════════════════════════════════════════════════════
# url
# ════════════════════════════════════════════════════════════════════════════════

class Test__Url:

    def test_1__url_missing_slug_exits_nonzero(self):
        fargate = _default_fargate()                                               # no tasks
        result  = _run(['url', '--slug', 'no-such-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code != 0

    def test_2__url_resolves_task_arn_required(self):
        # Task exists but has no ENI → no IP → exits nonzero with "No IP" message
        fargate = _fargate_with_running_task('url-vault')
        result  = _run(['url', '--slug', 'url-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        # exits nonzero because no IP is available in in-memory task
        assert result.exit_code != 0

    def test_3__url_auto_resolves_sole_task(self):
        # Single running task, no --slug needed — exits nonzero due to no IP but resolves slug
        fargate = _fargate_with_running_task('sole-vault')
        result  = _run(['url', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        # Any exit is fine here; we test that no "ambiguous slug" error fires
        assert 'No running task' not in result.output


# ════════════════════════════════════════════════════════════════════════════════
# logs
# ════════════════════════════════════════════════════════════════════════════════

class Test__Logs:

    def test_1__logs_no_events_prints_no_events_message(self):
        fargate = _fargate_with_running_task('logs-vault')
        result  = _run(['logs', '--slug', 'logs-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        assert 'No log events found' in result.output

    def test_2__logs_with_events_prints_stream_message(self):
        import time
        fargate = _fargate_with_running_task('logs-vault')
        logs    = Logs__AWS__Client__In_Memory()
        logs.seed_event('/ecs/vault-app', 'logs-vault', 'Hello from vault',
                        timestamp_ms=int(time.time() * 1000))                    # current time — within the 30-min filter window
        result  = _run(['logs', '--slug', 'logs-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate, logs=logs))
        assert result.exit_code == 0
        assert '[logs-vault]' in result.output
        assert 'Hello from vault' in result.output

    def test_3__logs_missing_slug_exits_nonzero(self):
        fargate = _default_fargate()                                               # no tasks
        result  = _run(['logs', '--slug', 'no-such', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code != 0

    def test_4__logs_since_flag_accepted(self):
        fargate = _fargate_with_running_task('logs-vault')
        result  = _run(['logs', '--slug', 'logs-vault', '--cluster', 'test-cluster',
                        '--since', '10'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0


# ════════════════════════════════════════════════════════════════════════════════
# list
# ════════════════════════════════════════════════════════════════════════════════

class Test__List:

    def test_1__list_no_tasks_prints_message(self):
        fargate = _default_fargate()                                               # no tasks
        result  = _run(['list', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        assert 'No running tasks found' in result.output

    def test_2__list_with_task_renders_table(self):
        fargate = _fargate_with_running_task('listed-vault')
        result  = _run(['list', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        assert 'listed-vault' in result.output

    def test_3__list_json_returns_array(self):
        fargate = _fargate_with_running_task('listed-vault')
        result  = _run(['list', '--cluster', 'test-cluster', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_4__list_json_has_required_fields(self):
        fargate = _fargate_with_running_task('listed-vault')
        result  = _run(['list', '--cluster', 'test-cluster', '--json'],
                       obj=_default_obj(fargate=fargate))
        data = json.loads(result.output)
        row = data[0]
        assert 'slug' in row
        assert 'task_arn' in row
        assert 'status' in row

    def test_5__list_json_slug_matches(self):
        fargate = _fargate_with_running_task('listed-vault')
        result  = _run(['list', '--cluster', 'test-cluster', '--json'],
                       obj=_default_obj(fargate=fargate))
        data = json.loads(result.output)
        assert data[0]['slug'] == 'listed-vault'

    def test_6__list_clusters_renders_cluster_names(self):
        fargate = _default_fargate()
        result  = _run(['list', '--clusters'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        assert 'test-cluster' in result.output

    def test_7__list_clusters_json_returns_array(self):
        fargate = _default_fargate()
        result  = _run(['list', '--clusters', '--json'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_8__list_clusters_json_has_cluster_name(self):
        fargate = _default_fargate()
        result  = _run(['list', '--clusters', '--json'],
                       obj=_default_obj(fargate=fargate))
        data = json.loads(result.output)
        names = [c['cluster_name'] for c in data]
        assert 'test-cluster' in names

    def test_9__list_no_clusters_prints_no_clusters_message(self):
        fargate = Fargate__AWS__Client__In_Memory()                                # no clusters at all
        result  = _run(['list', '--clusters'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0
        assert 'No ECS clusters found' in result.output


# ════════════════════════════════════════════════════════════════════════════════
# info
# ════════════════════════════════════════════════════════════════════════════════

class Test__Info:

    def test_1__info_missing_slug_exits_nonzero(self):
        fargate = _default_fargate()                                               # no tasks
        result  = _run(['info', '--slug', 'no-such', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code != 0

    def test_2__info_renders_task_panel(self):
        fargate = _fargate_with_running_task('info-vault')
        result  = _run(['info', '--slug', 'info-vault', '--cluster', 'test-cluster'],
                       obj=_default_obj(fargate=fargate))
        assert result.exit_code == 0, result.output
        assert 'info-vault' in result.output
        assert 'cluster' in result.output

    def test_3__info_shows_no_timing_records_when_store_empty(self):
        fargate = _fargate_with_running_task('info-vault')
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            tmp_path = f.name
        store   = Vault_App__Fargate__Timings__Store(path=tmp_path)
        result  = _run(['info', '--slug', 'info-vault', '--cluster', 'test-cluster'],
                       obj={**_default_obj(fargate=fargate), 'timings_store': store})
        assert result.exit_code == 0
        assert 'No timing records' in result.output

    def test_4__info_shows_timing_when_store_has_matching_records(self):
        fargate = _fargate_with_running_task('info-vault')
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            tmp_path = f.name
        store = Vault_App__Fargate__Timings__Store(path=tmp_path)
        store.append(Schema__VAF__Timings__Record(
            slug='info-vault', cluster_name='test-cluster',
            task_ready_ms=3000, vault_ready_ms=8000, total_ms=10000,
            executed_at='2026-05-19T10:00:00Z'))
        result = _run(['info', '--slug', 'info-vault', '--cluster', 'test-cluster'],
                      obj={**_default_obj(fargate=fargate), 'timings_store': store})
        assert result.exit_code == 0
        assert '3000ms' in result.output


# ════════════════════════════════════════════════════════════════════════════════
# timings
# ════════════════════════════════════════════════════════════════════════════════

class Test__Timings:

    def _make_store_with_records(self, n: int = 3) -> Vault_App__Fargate__Timings__Store:
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            tmp_path = f.name
        store = Vault_App__Fargate__Timings__Store(path=tmp_path)
        for i in range(n):
            store.append(Schema__VAF__Timings__Record(
                slug='my-vault', cluster_name='test-cluster',
                task_ready_ms=3000 + i * 100,
                vault_ready_ms=8000 + i * 100,
                total_ms=10000 + i * 100,
                launch_type='FARGATE',
                executed_at=f'2026-05-19T{i:02d}:00:00Z'))
        return store

    def test_1__timings_empty_store_prints_no_records_message(self):
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            tmp_path = f.name
        store  = Vault_App__Fargate__Timings__Store(path=tmp_path)
        result = _run(['timings'],
                      obj={**_default_obj(), 'timings_store': store})
        assert result.exit_code == 0
        assert 'No timing records found' in result.output

    def test_2__timings_json_returns_array(self):
        store  = self._make_store_with_records(3)
        result = _run(['timings', '--json'],
                      obj={**_default_obj(), 'timings_store': store})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_3__timings_json_has_required_fields(self):
        store  = self._make_store_with_records(1)
        result = _run(['timings', '--json'],
                      obj={**_default_obj(), 'timings_store': store})
        data = json.loads(result.output)
        rec  = data[0]
        assert 'slug'            in rec
        assert 'cluster_name'    in rec
        assert 'task_ready_ms'   in rec
        assert 'vault_ready_ms'  in rec
        assert 'total_ms'        in rec
        assert 'executed_at'     in rec

    def test_4__timings_last_flag_limits_records(self):
        store  = self._make_store_with_records(10)
        result = _run(['timings', '--last', '5', '--json'],
                      obj={**_default_obj(), 'timings_store': store})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) <= 5

    def test_5__timings_slug_filter_json(self):
        store  = self._make_store_with_records(3)
        # add a record with different slug
        store.append(Schema__VAF__Timings__Record(
            slug='other-vault', cluster_name='test-cluster',
            task_ready_ms=1000, vault_ready_ms=2000, total_ms=3000,
            executed_at='2026-05-19T05:00:00Z'))
        result = _run(['timings', '--slug', 'my-vault', '--json'],
                      obj={**_default_obj(), 'timings_store': store})
        data   = json.loads(result.output)
        assert all(r['slug'] == 'my-vault' for r in data)

    def test_6__timings_cluster_filter_json(self):
        store  = self._make_store_with_records(3)
        store.append(Schema__VAF__Timings__Record(
            slug='other-vault', cluster_name='other-cluster',
            task_ready_ms=1000, vault_ready_ms=2000, total_ms=3000,
            executed_at='2026-05-19T06:00:00Z'))
        result = _run(['timings', '--cluster', 'test-cluster', '--json'],
                      obj={**_default_obj(), 'timings_store': store})
        data   = json.loads(result.output)
        assert all(r['cluster_name'] == 'test-cluster' for r in data)

    def test_7__timings_renders_table_by_default(self):
        store  = self._make_store_with_records(2)
        result = _run(['timings'],
                      obj={**_default_obj(), 'timings_store': store})
        assert result.exit_code == 0
        assert 'my-vault' in result.output


# ════════════════════════════════════════════════════════════════════════════════
# parent app integration
# ════════════════════════════════════════════════════════════════════════════════

class Test__Fargate_App_Integration:

    def test_1__fargate_app_has_start_command(self):
        names = [c.name for c in fargate_app.registered_commands]
        assert 'start' in names

    def test_2__fargate_app_has_stop_command(self):
        names = [c.name for c in fargate_app.registered_commands]
        assert 'stop' in names

    def test_3__fargate_app_has_all_task_commands(self):
        names = [c.name for c in fargate_app.registered_commands]
        for cmd in ('start', 'stop', 'restart', 'health', 'url', 'open',
                    'logs', 'list', 'info', 'timings'):
            assert cmd in names, f'Missing command: {cmd}'

    def test_4__fargate_app_still_has_setup_group(self):
        names = [g.name for g in getattr(fargate_app, 'registered_groups', [])]
        assert 'setup' in names

    def test_5__fargate_app_start_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = runner.invoke(fargate_app, ['start', '--yes', '--cluster', 'test-cluster'],
                               obj=_default_obj())
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_6__fargate_app_list_clusters_via_parent(self):
        result = runner.invoke(fargate_app, ['list', '--clusters', '--json'],
                               obj=_default_obj())
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
