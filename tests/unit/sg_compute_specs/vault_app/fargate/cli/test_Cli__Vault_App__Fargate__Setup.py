# ═══════════════════════════════════════════════════════════════════════════════
# Tests — test_Cli__Vault_App__Fargate__Setup
# CLI-level tests for `sg vault-app fargate setup *` commands.
# Uses Typer CliRunner + in-memory clients injected via ctx.obj.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import pytest
from typer.testing import CliRunner

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate__Setup import app
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Image__Mirror import Vault_App__Fargate__Image__Mirror

from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory     import ECR__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory    import IAM__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory  import Logs__AWS__Client__In_Memory

runner   = CliRunner()
_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok_runner(cmd: list) -> tuple:                                              # succeeds for all docker commands
    if 'inspect' in cmd:
        return (0, 'sha256:abc123deadbeef', '')
    return (0, '', '')


def _default_obj():
    ecr     = ECR__AWS__Client__In_Memory()
    fargate = Fargate__AWS__Client__In_Memory()
    iam     = IAM__AWS__Client__In_Memory()
    logs    = Logs__AWS__Client__In_Memory()
    return {
        'ecr_client'    : ecr,
        'fargate_client': fargate,
        'iam_client'    : iam,
        'logs_client'   : logs,
    }


def _seeded_obj():
    ecr     = ECR__AWS__Client__In_Memory()
    fargate = Fargate__AWS__Client__In_Memory()
    iam     = IAM__AWS__Client__In_Memory()
    logs    = Logs__AWS__Client__In_Memory()
    ecr.seed_repo('sg-send-vault')
    fargate.seed_cluster_with_tags('vault-app', {
        'Stack'                    : 'sg-vault-app-fargate',
        'VaultApp__Subnets'        : 'subnet-aaa',
        'VaultApp__SecurityGroup'  : 'sg-xxx',
        'VaultApp__LogGroup'       : '/ecs/vault-app',
        'VaultApp__EcrRepoName'    : 'sg-send-vault',
        'VaultApp__Region'         : 'us-east-1',
    })
    return {
        'ecr_client'    : ecr,
        'fargate_client': fargate,
        'iam_client'    : iam,
        'logs_client'   : logs,
    }


def _run(args, obj=None):
    return runner.invoke(app, args, obj=obj if obj is not None else _default_obj())


# ════════════════════════════════════════════════════════════════════════════════
# check
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Check:

    def test_1__check_no_cluster_option_exits_ok(self):
        result = _run(['check', '--cluster', 'test-cluster'])
        assert result.exit_code == 0

    def test_2__check_json_returns_valid_json(self):
        result = _run(['check', '--cluster', 'test-cluster', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'phases' in data
        assert 'ok' in data

    def test_3__check_json_has_phases_array(self):
        result = _run(['check', '--cluster', 'test-cluster', '--json'])
        data = json.loads(result.output)
        assert isinstance(data['phases'], list)
        assert len(data['phases']) == 6                                          # all 6 phases

    def test_4__check_json_phases_have_required_fields(self):
        result = _run(['check', '--cluster', 'test-cluster', '--json'])
        data = json.loads(result.output)
        for phase in data['phases']:
            assert 'name' in phase
            assert 'status' in phase
            assert 'duration_ms' in phase
            assert 'detail' in phase

    def test_5__check_phase_ecr_only(self):
        result = _run(['check', '--cluster', 'test-cluster', '--phase', 'ecr', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'ECR'

    def test_6__check_phase_iam_only(self):
        result = _run(['check', '--cluster', 'test-cluster', '--phase', 'iam', '--json'])
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'IAM'

    def test_7__check_operation_is_check_in_json(self):
        result = _run(['check', '--cluster', 'test-cluster', '--json'])
        data = json.loads(result.output)
        assert data['operation'] == 'check'

    def test_8__check_cluster_name_in_json(self):
        result = _run(['check', '--cluster', 'my-cluster', '--json'])
        data = json.loads(result.output)
        assert data['cluster_name'] == 'my-cluster'

    def test_9__check_phase_all_returns_six_phases(self):
        result = _run(['check', '--cluster', 'test-cluster', '--phase', 'all', '--json'])
        data = json.loads(result.output)
        assert len(data['phases']) == 6

    def test_10__check_image_mirror_phase_name(self):
        result = _run(['check', '--cluster', 'test-cluster', '--phase', 'image-mirror', '--json'])
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'IMAGE_MIRROR'

    def test_11__check_invalid_phase_exits_nonzero(self):
        result = _run(['check', '--cluster', 'test-cluster', '--phase', 'bogus'])
        assert result.exit_code != 0


# ════════════════════════════════════════════════════════════════════════════════
# status
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Status:

    def test_1__status_json_has_six_phases(self):
        result = _run(['status', '--cluster', 'test-cluster', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data['phases']) == 6

    def test_2__status_operation_is_check(self):
        result = _run(['status', '--cluster', 'test-cluster', '--json'])
        data = json.loads(result.output)
        assert data['operation'] == 'check'


# ════════════════════════════════════════════════════════════════════════════════
# create
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Create:

    def test_1__create_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = _run(['create', '--cluster', 'test-cluster', '--yes'])
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__create_with_gate_json_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        ecr     = ECR__AWS__Client__In_Memory()
        fargate = Fargate__AWS__Client__In_Memory()
        iam     = IAM__AWS__Client__In_Memory()
        logs    = Logs__AWS__Client__In_Memory()
        mirror  = Vault_App__Fargate__Image__Mirror()
        mirror._runner = _ok_runner
        ecr.seed_repo('sg-send-vault')
        obj = {
            'ecr_client'    : ecr,
            'fargate_client': fargate,
            'iam_client'    : iam,
            'logs_client'   : logs,
        }
        result = _run(['create', '--cluster', 'test-cluster', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['operation'] == 'create'
        assert data['cluster_name'] == 'test-cluster'

    def test_3__create_json_has_phases(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj    = _default_obj()
        obj['ecr_client'].seed_repo('sg-send-vault')
        result = _run(['create', '--cluster', 'test-cluster', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data['phases'], list)
        assert len(data['phases']) > 0

    def test_4__create_json_ok_field_present(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _default_obj()
        obj['ecr_client'].seed_repo('sg-send-vault')
        result = _run(['create', '--cluster', 'test-cluster', '--yes', '--json'], obj=obj)
        data = json.loads(result.output)
        assert 'ok' in data

    def test_5__create_json_total_ms_present(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _default_obj()
        obj['ecr_client'].seed_repo('sg-send-vault')
        result = _run(['create', '--cluster', 'test-cluster', '--yes', '--json'], obj=obj)
        data = json.loads(result.output)
        assert 'total_ms' in data
        assert isinstance(data['total_ms'], int)

    def test_6__create_ecr_phase_subset_json(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _default_obj()
        result = _run(['create', '--cluster', 'test-cluster',
                       '--phase', 'ecr', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'ECR'

    def test_7__create_sets_inner_mutation_gates(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        obj = _default_obj()
        result = _run(['create', '--cluster', 'test-cluster',
                       '--phase', 'ecr', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output                              # inner gate was unlocked


# ════════════════════════════════════════════════════════════════════════════════
# update
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Update:

    def test_1__update_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = _run(['update', '--cluster', 'test-cluster', '--yes'])
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__update_with_gate_json_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['update', '--cluster', 'vault-app', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['operation'] == 'update'

    def test_3__update_json_has_phases(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['update', '--cluster', 'vault-app', '--yes', '--json'], obj=obj)
        data = json.loads(result.output)
        assert isinstance(data['phases'], list)

    def test_4__update_phase_subset(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _default_obj()
        result = _run(['update', '--cluster', 'test-cluster',
                       '--phase', 'logs', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'LOGS'


# ════════════════════════════════════════════════════════════════════════════════
# delete
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Delete:

    def test_1__delete_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = _run(['delete', '--cluster', 'test-cluster', '--yes'])
        assert result.exit_code == 1
        assert _GATE_ENV in result.output

    def test_2__delete_with_gate_json_exits_ok(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['delete', '--cluster', 'vault-app', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['operation'] == 'delete'

    def test_3__delete_json_phases_reversed(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['delete', '--cluster', 'vault-app', '--yes', '--json'], obj=obj)
        data = json.loads(result.output)
        names = [p['name'] for p in data['phases']]
        assert names[0]  == 'TASK_DEF'                                           # reversed order starts with TASK_DEF
        assert names[-1] == 'ECR'                                                # ECR is last

    def test_4__delete_all_six_phases_in_reverse(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['delete', '--cluster', 'vault-app', '--yes', '--json'], obj=obj)
        data = json.loads(result.output)
        assert len(data['phases']) == 6

    def test_5__delete_phase_subset(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj = _seeded_obj()
        result = _run(['delete', '--cluster', 'vault-app',
                       '--phase', 'cluster', '--yes', '--json'], obj=obj)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'CLUSTER'


# ════════════════════════════════════════════════════════════════════════════════
# plan
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Plan:

    def test_1__plan_read_only_no_gate_needed(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        result = _run(['plan', '--cluster', 'test-cluster'])
        assert result.exit_code == 0                                             # no gate required

    def test_2__plan_json_exits_ok(self):
        result = _run(['plan', '--cluster', 'test-cluster', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['operation'] == 'plan'

    def test_3__plan_json_has_phases(self):
        result = _run(['plan', '--cluster', 'test-cluster', '--json'])
        data = json.loads(result.output)
        assert isinstance(data['phases'], list)
        assert len(data['phases']) == 6

    def test_4__plan_phase_subset(self):
        result = _run(['plan', '--cluster', 'test-cluster', '--phase', 'ecr', '--json'])
        data = json.loads(result.output)
        assert len(data['phases']) == 1
        assert data['phases'][0]['name'] == 'ECR'

    def test_5__plan_does_not_mutate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        fargate = Fargate__AWS__Client__In_Memory()
        obj     = _default_obj()
        obj['fargate_client'] = fargate
        _run(['plan', '--cluster', 'test-cluster', '--json'], obj=obj)
        assert len(fargate._clusters) == 0                                       # nothing was created


# ════════════════════════════════════════════════════════════════════════════════
# show
# ════════════════════════════════════════════════════════════════════════════════

class Test__Setup__Show:

    def test_1__show_cluster_with_tags_exits_ok(self):
        obj    = _seeded_obj()
        result = _run(['show', '--cluster', 'vault-app'], obj=obj)
        assert result.exit_code == 0

    def test_2__show_renders_cluster_config(self):
        obj    = _seeded_obj()
        result = _run(['show', '--cluster', 'vault-app'], obj=obj)
        assert 'cluster name' in result.output
        assert 'vault-app'    in result.output

    def test_3__show_renders_subnet_info(self):
        obj    = _seeded_obj()
        result = _run(['show', '--cluster', 'vault-app'], obj=obj)
        assert 'subnet-aaa' in result.output

    def test_4__show_missing_cluster_shows_not_set(self):
        # resolver returns the explicit name; describe_cluster returns None → empty config
        obj    = _default_obj()
        result = _run(['show', '--cluster', 'no-such-cluster'], obj=obj)
        assert result.exit_code == 0
        assert '(not set)' in result.output or 'no-such-cluster' in result.output

    def test_5__show_no_task_def_shows_no_task_def_message(self):
        obj    = _seeded_obj()
        result = _run(['show', '--cluster', 'vault-app'], obj=obj)
        assert 'No task definition' in result.output                             # none registered

    def test_6__show_with_task_def_renders_task_def_table(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        obj    = _seeded_obj()
        # Register a task definition in the in-memory fargate client
        obj['fargate_client'].register_task_definition(
            name='vault-app', image='img:latest', cpu='512', memory='1024')
        result = _run(['show', '--cluster', 'vault-app'], obj=obj)
        assert result.exit_code == 0
        assert 'family' in result.output


# ════════════════════════════════════════════════════════════════════════════════
# parent app (Cli__Vault_App__Fargate)
# ════════════════════════════════════════════════════════════════════════════════

class Test__Cli__Vault_App__Fargate:

    def test_1__fargate_app_mounts_setup(self):
        from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app
        from typer.testing import CliRunner as TR
        r      = TR()
        result = r.invoke(fargate_app, ['setup', 'check', '--cluster', 'test-cluster', '--json'],
                          obj=_default_obj())
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['operation'] == 'check'

    def test_2__fargate_app_has_setup_group(self):
        from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app
        names = [g.name for g in getattr(fargate_app, 'registered_groups', [])]
        assert 'setup' in names
