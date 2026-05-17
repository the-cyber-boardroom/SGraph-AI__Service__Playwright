# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Iam
# Tests for sg aws iam role list / show / check via CliRunner.
# Mutations are not exercised here (they require SG_AWS__IAM__ALLOW_MUTATIONS=1).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam import iam_app
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory import IAM__AWS__Client__In_Memory


runner = CliRunner()


def _seed_client(client: IAM__AWS__Client__In_Memory):
    from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service      import Enum__IAM__Trust__Service
    from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name  import Safe_Str__IAM__Role_Name
    from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
    client.create_role(Schema__IAM__Role__Create__Request(
        role_name=Safe_Str__IAM__Role_Name('sg-waker-role'),
        trust_service=Enum__IAM__Trust__Service.LAMBDA))
    return client


class Test__Cli__Iam:

    def test_1__role_list_empty(self, monkeypatch):
        client = IAM__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam._client', lambda: client)
        result = runner.invoke(iam_app, ['role', 'list'])
        assert result.exit_code == 0
        assert 'No IAM roles' in result.output

    def test_2__role_list_json(self, monkeypatch):
        client = _seed_client(IAM__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam._client', lambda: client)
        result = runner.invoke(iam_app, ['role', 'list', '--json'])
        assert result.exit_code == 0
        data   = json.loads(result.output)
        assert any(r['role_name'] == 'sg-waker-role' for r in data)

    def test_3__role_show_existing(self, monkeypatch):
        client = _seed_client(IAM__AWS__Client__In_Memory())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam._client', lambda: client)
        result = runner.invoke(iam_app, ['role', 'show', 'sg-waker-role', '--json'])
        assert result.exit_code == 0
        data   = json.loads(result.output)
        assert data['role_name'] == 'sg-waker-role'

    def test_4__role_show_missing(self, monkeypatch):
        client = IAM__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam._client', lambda: client)
        result = runner.invoke(iam_app, ['role', 'show', 'no-such-role'])
        assert result.exit_code == 1

    def test_5__role_check_clean(self, monkeypatch):
        from sgraph_ai_service_playwright__cli.aws.iam.service.templates.Waker__Policy__Template import Waker__Policy__Template
        client = _seed_client(IAM__AWS__Client__In_Memory())
        client.put_inline_policy('sg-waker-role', 'permissions', Waker__Policy__Template().build())
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.iam.cli.Cli__Iam._client', lambda: client)
        result = runner.invoke(iam_app, ['role', 'check', 'sg-waker-role', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['overall_severity'] == 'INFO'
        critical = [f for f in data['findings'] if f['severity'] == 'CRITICAL']
        assert len(critical) == 0

    def test_6__create_requires_mutation_guard(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__IAM__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(iam_app, ['role', 'create', 'new-role', '--trust-service', 'lambda'])
        assert result.exit_code == 1
        assert 'SG_AWS__IAM__ALLOW_MUTATIONS' in result.output
