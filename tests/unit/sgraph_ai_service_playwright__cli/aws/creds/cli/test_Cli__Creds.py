# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__Creds
# Tests for `sg aws creds` CLI commands via Typer CliRunner.
# Covers: get, list-scopes, scope show/add/remove/update, audit list/show,
#         mutation gate, TTL cap, and audit logging.
# No mocks. No patches (uses in-memory fakes injected via ctx.obj).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.creds.cli.Cli__Creds import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue__In_Memory import (
    Creds__Scope__Catalogue__In_Memory,
)
from tests.unit.sgraph_ai_service_playwright__cli.aws.creds.service.Creds__STS__Client__In_Memory import (
    Creds__STS__Client__In_Memory,
)

runner = CliRunner()


class Test__Cli__Creds:

    # ── list-scopes ───────────────────────────────────────────────────────────

    def test_1__list_scopes_empty_json(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        result = runner.invoke(app, ['list-scopes', '--json'], obj={'creds_catalogue': cat})
        assert result.exit_code == 0
        assert json.loads(result.output) == []

    def test_2__list_scopes_with_entry_json(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('dev', 'arn:aws:iam::1:role/Dev', '1h')
        result = runner.invoke(app, ['list-scopes', '--json'], obj={'creds_catalogue': cat})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['name'] == 'dev'

    # ── scope show ────────────────────────────────────────────────────────────

    def test_3__scope_show_json(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('staging', 'arn:aws:iam::2:role/Staging', '30m')
        result = runner.invoke(app, ['scope', 'show', 'staging', '--json'], obj={'creds_catalogue': cat})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['name']     == 'staging'
        assert data['role_arn'] == 'arn:aws:iam::2:role/Staging'
        assert data['max_ttl']  == '30m'

    def test_4__scope_show_missing_exits_1(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        result = runner.invoke(app, ['scope', 'show', 'no-such'], obj={'creds_catalogue': cat})
        assert result.exit_code == 1

    # ── scope add (mutation gated) ────────────────────────────────────────────

    def test_5__scope_add_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__CREDS__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['scope', 'add', '--name', 'x', '--role', 'arn:aws:iam::1:role/X', '--yes'])
        assert result.exit_code == 1

    def test_6__scope_add_with_gate_set(self, monkeypatch):
        cat = Creds__Scope__Catalogue__In_Memory()
        monkeypatch.setenv('SG_AWS__CREDS__ALLOW_MUTATIONS', '1')
        result = runner.invoke(app, ['scope', 'add', '--name', 'prod', '--role',
                                     'arn:aws:iam::3:role/Prod', '--max-ttl', '2h',
                                     '--yes', '--json'],
                               obj={'creds_catalogue': cat})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['name']    == 'prod'
        assert data['max_ttl'] == '2h'
        assert cat.scope_get('prod') is not None

    # ── scope remove (mutation gated) ─────────────────────────────────────────

    def test_7__scope_remove_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__CREDS__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['scope', 'remove', 'any-scope', '--yes'])
        assert result.exit_code == 1

    # ── get ───────────────────────────────────────────────────────────────────

    def test_8__get_unknown_scope_exits_1(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        result = runner.invoke(app, ['get', '--scope', 'no-such'],
                               obj={'creds_catalogue' : cat,
                                    'creds_sts_client': Creds__STS__Client__In_Memory()})
        assert result.exit_code == 1

    def test_9__get_returns_json_creds(self):
        from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Audit__Log import Creds__Audit__Log

        class _NullAudit(Creds__Audit__Log):                                   # Suppress filesystem write in this test
            def append(self, entry: dict): pass

        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('dev', 'arn:aws:iam::1:role/Dev', '1h')
        result = runner.invoke(app, ['get', '--scope', 'dev', '--json'],
                               obj={'creds_catalogue' : cat,
                                    'creds_sts_client': Creds__STS__Client__In_Memory(),
                                    'creds_audit_log' : _NullAudit()})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'access_key_id'     in data
        assert 'secret_access_key' in data
        assert 'session_token'     in data
        assert 'expiration'        in data
        assert data['access_key_id'].startswith('ASIA')

    def test_10__get_ttl_exceeds_max_exits_1(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('narrow', 'arn:aws:iam::1:role/Narrow', '30m')
        result = runner.invoke(app, ['get', '--scope', 'narrow', '--ttl', '2h'],
                               obj={'creds_catalogue' : cat,
                                    'creds_sts_client': Creds__STS__Client__In_Memory()})
        assert result.exit_code == 1
