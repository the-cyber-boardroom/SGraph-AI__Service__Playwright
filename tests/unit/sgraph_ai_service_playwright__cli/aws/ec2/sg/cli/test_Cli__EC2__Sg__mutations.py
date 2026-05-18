# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Sg mutating commands
# CLI tests for `sg aws ec2 sg delete` via Typer CliRunner. No mocks, no
# patches — the in-memory client is injected via ctx.obj. Each test that
# should reach the command body sets SG_AWS__EC2__ALLOW_MUTATIONS=1 via
# monkeypatch; gate-blocked tests delete the env var.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Sg import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__Cli__EC2__Sg__Mutations:

    # ── mutation gate ────────────────────────────────────────────────────────

    def test_1__delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1
        assert client.describe_security_group('sg-aaaaaaaa') is not None

    # ── happy path ───────────────────────────────────────────────────────────

    def test_2__delete_with_yes_empty_sg(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert client.describe_security_group('sg-aaaaaaaa') is None

    # ── attached-ENI hard guard ──────────────────────────────────────────────

    def test_3__delete_refuses_when_attached(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_network_interface(eni_id='eni-11111111',
                                       sg_ids=['sg-aaaaaaaa'],
                                       instance_id='i-12345678')
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1
        # SG still exists — delete_security_group was never called
        assert client.describe_security_group('sg-aaaaaaaa') is not None
        # red panel mentions the ENI
        assert 'eni-11111111' in result.output

    # ── not-found ────────────────────────────────────────────────────────────

    def test_4__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['delete', 'sg-deadbeef', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    # ── ambiguous-name path ──────────────────────────────────────────────────

    def test_5__delete_ambiguous_name_errors(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='shared',
                                    vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='shared',
                                    vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['delete', 'shared', '--yes'],
                               obj=_obj(client))
        # describe raises ValueError → _resolve_sg → typer.BadParameter → exit 2
        assert result.exit_code != 0
        # both SGs preserved
        assert client.describe_security_group('sg-aaaaaaaa') is not None
        assert client.describe_security_group('sg-bbbbbbbb') is not None

    # ── confirm-no aborts ────────────────────────────────────────────────────

    def test_6__delete_no_confirm_aborts(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa'],
                               input='n\n', obj=_obj(client))
        assert result.exit_code == 0
        assert client.describe_security_group('sg-aaaaaaaa') is not None

    # ── JSON output ──────────────────────────────────────────────────────────

    def test_7__delete_json_happy_path(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['sg_id']   == 'sg-aaaaaaaa'
        assert data['deleted'] is True

    def test_8__delete_json_attached_guard(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_network_interface(eni_id='eni-11111111',
                                       sg_ids=['sg-aaaaaaaa'])
        result = runner.invoke(app, ['delete', 'sg-aaaaaaaa', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data['sg_id']            == 'sg-aaaaaaaa'
        assert data['deleted']          is False
        assert data['error']            == 'attached'
        assert data['attached_eni_ids'] == ['eni-11111111']
