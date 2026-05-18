# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Ecr
# CLI tests for `sg aws ecr` via Typer CliRunner. No mocks. No patches —
# the in-memory client is injected through ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ecr.cli.Cli__Ecr import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory import ECR__AWS__Client__In_Memory

runner = CliRunner()


def _obj(client):
    return {'ecr_client': client}


class Test__Cli__Ecr:

    # ── repos ────────────────────────────────────────────────────────────────

    def test_1__repos_empty(self):
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['repos'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'No repositories found' in result.output

    def test_2__repos_json(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha', scan_on_push=True)
        client.seed_repo('beta')
        result = runner.invoke(app, ['repos', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = sorted(r['name'] for r in data)
        assert names == ['alpha', 'beta']

    def test_3__repos_table(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['repos'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'alpha' in result.output

    # ── repo ─────────────────────────────────────────────────────────────────

    def test_4__repo_missing(self):
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['repo', 'nope'], obj=_obj(client))
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_5__repo_json(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'], size=1000)
        client.seed_image('alpha', tags=['v2'], size=2000)
        result = runner.invoke(app, ['repo', 'alpha', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['name']             == 'alpha'
        assert data['image_count']      == 2
        assert data['total_size_bytes'] == 3000

    # ── images ───────────────────────────────────────────────────────────────

    def test_6__images_missing_repo(self):
        client = ECR__AWS__Client__In_Memory()
        result = runner.invoke(app, ['images', 'nope'], obj=_obj(client))
        assert result.exit_code == 1

    def test_7__images_empty(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['images', 'alpha'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'No images found' in result.output

    def test_8__images_json(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'], size=512)
        result = runner.invoke(app, ['images', 'alpha', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['tags'] == ['v1']
        assert data[0]['size_bytes'] == 512

    def test_9__images_untagged_filter(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        client.seed_image('alpha', tags=[])
        result = runner.invoke(app, ['images', 'alpha', '--untagged', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['tags'] == []

    def test_10__images_older_filter(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['old'],
                          pushed_at=datetime.now(timezone.utc) - timedelta(days=60))
        client.seed_image('alpha', tags=['new'],
                          pushed_at=datetime.now(timezone.utc))
        result = runner.invoke(app, ['images', 'alpha', '--older', '30d', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['tags'] == ['old']

    def test_11__images_older_invalid(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['images', 'alpha', '--older', 'banana'],
                               obj=_obj(client))
        assert result.exit_code != 0

    def test_12__images_digest_column(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        digest = client.seed_image('alpha', tags=['v1'])
        result = runner.invoke(app, ['images', 'alpha', '--digest'], obj=_obj(client))
        assert result.exit_code == 0
        assert digest[:20] in result.output                                      # digest column appears

    # ── image ────────────────────────────────────────────────────────────────

    def test_13__image_missing(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['image', 'alpha', 'nope'], obj=_obj(client))
        assert result.exit_code == 1

    def test_14__image_json(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        digest = client.seed_image('alpha', tags=['v1'], size=777)
        result = runner.invoke(app, ['image', 'alpha', 'v1', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['digest']     == digest
        assert data['size_bytes'] == 777

    # ── scan ─────────────────────────────────────────────────────────────────

    def test_15__scan_missing(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        result = runner.invoke(app, ['scan', 'alpha', 'nope'], obj=_obj(client))
        assert result.exit_code == 1

    def test_16__scan_json(self):
        client = ECR__AWS__Client__In_Memory()
        client.seed_repo('alpha')
        client.seed_image('alpha', tags=['v1'], scan=dict(
            status       = 'COMPLETE',
            completed_at = datetime.now(timezone.utc),
            counts       = {'CRITICAL': 1, 'HIGH': 2},
        ))
        result = runner.invoke(app, ['scan', 'alpha', 'v1', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['status']            == 'COMPLETE'
        assert data['counts']['critical'] == 1
        assert data['counts']['high']     == 2
