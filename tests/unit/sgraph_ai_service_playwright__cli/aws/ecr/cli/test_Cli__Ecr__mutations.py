# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Ecr mutating commands
# CLI tests for `sg aws ecr {prune,delete,repo-create,repo-delete}` via Typer
# CliRunner. No mocks, no patches — the in-memory client is injected through
# ctx.obj. Each test that should reach the body sets SG_AWS__ECR__ALLOW_MUTATIONS=1
# via monkeypatch; gate-blocked tests delete the env var.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ecr.cli.Cli__Ecr                                  import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory import ECR__AWS__Client__In_Memory

runner = CliRunner()


def _obj(client):
    return {'ecr_client': client}


class Test__Cli__Ecr__Mutations:

    # ── mutation gate (env var not set) ──────────────────────────────────────

    def test_1__prune_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['prune', 'alpha', '--yes'])
        assert result.exit_code == 1

    def test_2__delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['delete', 'alpha', 'v1', '--yes'])
        assert result.exit_code == 1

    def test_3__repo_create_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['repo-create', 'alpha'])
        assert result.exit_code == 1

    def test_4__repo_delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__ECR__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['repo-delete', 'alpha', '--yes'])
        assert result.exit_code == 1

    # ── prune ────────────────────────────────────────────────────────────────

    def test_5__prune_dry_run_does_not_delete(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=[], size=100)
        client.seed_image('alpha', tags=[], size=200)
        result = runner.invoke(app, ['prune', 'alpha', '--untagged', '--dry-run', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        # confirm nothing was deleted
        assert len(client.list_images('alpha')) == 2

    def test_6__prune_with_yes_deletes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=[])
        client.seed_image('alpha', tags=['keep'])
        result = runner.invoke(app, ['prune', 'alpha', '--untagged', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        remaining = client.list_images('alpha')
        assert len(remaining) == 1
        assert [str(t) for t in remaining[0].tags] == ['keep']

    def test_7__prune_json_dry_run(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=[])
        result = runner.invoke(app, ['prune', 'alpha', '--untagged',
                                     '--dry-run', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['executed']      is False
        assert data['deleted_count'] == 0
        assert 'plan' in data

    def test_8__prune_json_executed(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=[], size=100)
        client.seed_image('alpha', tags=[], size=200)
        result = runner.invoke(app, ['prune', 'alpha', '--untagged',
                                     '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['executed']      is True
        assert data['deleted_count'] == 2

    def test_9__prune_missing_repo(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['prune', 'nope', '--yes'], obj=_obj(client))
        assert result.exit_code == 1

    def test_10__prune_older_filter(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['old'],
                          pushed_at=datetime.now(timezone.utc) - timedelta(days=60))
        client.seed_image('alpha', tags=['new'],
                          pushed_at=datetime.now(timezone.utc))
        result = runner.invoke(app, ['prune', 'alpha', '--older', '30d',
                                     '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['executed']      is True
        assert data['deleted_count'] == 1
        remaining = client.list_images('alpha')
        assert [str(t) for img in remaining for t in img.tags] == ['new']

    # ── delete ───────────────────────────────────────────────────────────────

    def test_11__delete_with_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['delete', 'alpha', 'v1', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert client.describe_image('alpha', 'v1') is None

    def test_12__delete_missing_image_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['delete', 'alpha', 'nope', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1

    def test_13__delete_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['delete', 'alpha', 'v1', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deleted']       is True
        assert data['repo']          == 'alpha'
        assert data['tag_or_digest'] == 'v1'

    def test_14__delete_no_confirm_aborts(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        # decline the confirmation prompt
        result = runner.invoke(app, ['delete', 'alpha', 'v1'],
                               input='n\n', obj=_obj(client))
        assert result.exit_code == 0
        # image still present
        assert client.describe_image('alpha', 'v1') is not None

    # ── repo-create ──────────────────────────────────────────────────────────

    def test_15__repo_create_new(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['repo-create', 'brand-new'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'Created' in result.output
        assert client.describe_repository('brand-new') is not None

    def test_16__repo_create_already_exists(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['repo-create', 'alpha'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'Already exists' in result.output

    def test_17__repo_create_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['repo-create', 'brand-new', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['created'] is True
        assert data['name']    == 'brand-new'

    # ── repo-delete ──────────────────────────────────────────────────────────

    def test_18__repo_delete_with_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['repo-delete', 'alpha', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert client.describe_repository('alpha') is None

    def test_19__repo_delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['repo-delete', 'nope', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1

    def test_20__repo_delete_not_empty_without_force_raises(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['repo-delete', 'alpha', '--yes'],
                               obj=_obj(client))
        # surfaced via spec_cli_errors → non-zero exit
        assert result.exit_code != 0

    def test_21__repo_delete_force(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['repo-delete', 'alpha', '--force', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert client.describe_repository('alpha') is None

    def test_22__repo_delete_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['repo-delete', 'alpha', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deleted'] is True
        assert data['name']    == 'alpha'

    def test_23__repo_delete_aborts_on_no(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__ECR__ALLOW_MUTATIONS', '1')
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['repo-delete', 'alpha'],
                               input='n\n', obj=_obj(client))
        assert result.exit_code == 0
        # still exists
        assert client.describe_repository('alpha') is not None
