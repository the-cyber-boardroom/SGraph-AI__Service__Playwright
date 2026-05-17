# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2
# Tests for `sg aws ec2` CLI commands via Typer CliRunner.
# Covers: list, describe, tags, mutation gate, state enum.
# No mocks. No patches (except monkeypatching _client and _resolver to inject
# the in-memory client, which is the standard pattern in this codebase).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2 import app
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__Name__Resolver import EC2__Name__Resolver
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory

runner = CliRunner()


class Test__Cli__EC2:

    def test_1__list_empty(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        result = runner.invoke(app, ['list'])
        assert result.exit_code == 0
        assert 'No instances found' in result.output

    def test_2__list_json_with_instances(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='web-server', state='running', public_ip='1.2.3.4')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        result = runner.invoke(app, ['list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['instance_id'] == iid
        assert data[0]['name']        == 'web-server'
        assert data[0]['state']       == 'running'
        assert data[0]['public_ip']   == '1.2.3.4'

    def test_3__list_filter_state(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        client.seed_instance(name='running-srv', state='running')
        client.seed_instance(name='stopped-srv', state='stopped')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        result = runner.invoke(app, ['list', '--state', 'running', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['name'] == 'running-srv'

    def test_4__describe_json(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='my-host', public_ip='5.5.5.5')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._resolver',
                            lambda: EC2__Name__Resolver(ec2_client=client).setup())
        result = runner.invoke(app, ['describe', iid, '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['instance_id'] == iid
        assert data['name']        == 'my-host'
        assert data['public_ip']   == '5.5.5.5'

    def test_5__describe_not_found(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._resolver',
                            lambda: EC2__Name__Resolver(ec2_client=client).setup())
        result = runner.invoke(app, ['describe', 'no-such'])
        assert result.exit_code == 1

    def test_6__tags_view_json(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='tagged-srv')
        client.add_tags(iid, {'env': 'test'})
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._resolver',
                            lambda: EC2__Name__Resolver(ec2_client=client).setup())
        result = runner.invoke(app, ['tags', iid, '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get('env') == 'test'
        assert data.get('Name') == 'tagged-srv'

    def test_7__create_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['create', '--name', 'test', '--instance-type', 't3.micro',
                                     '--ami', 'ami-12345678', '--yes'])
        assert result.exit_code == 1

    def test_8__start_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['start', 'i-12345678', '--yes'])
        assert result.exit_code == 1

    def test_9__stop_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['stop', 'i-12345678', '--yes'])
        assert result.exit_code == 1

    def test_10__terminate_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        result = runner.invoke(app, ['terminate', 'i-12345678', '--yes'])
        assert result.exit_code == 1

    def test_11__create_with_gate_set(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        result = runner.invoke(app, ['create', '--name', 'test-host',
                                     '--instance-type', 't3.micro',
                                     '--ami', 'ami-12345678',
                                     '--no-wait', '--yes'])
        assert result.exit_code == 0
        assert 'Created' in result.output

    def test_12__instance_types_json(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        result = runner.invoke(app, ['instance-types', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_13__wait_invalid_state(self, monkeypatch):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._client', lambda: client)
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2._resolver',
                            lambda: EC2__Name__Resolver(ec2_client=client).setup())
        result = runner.invoke(app, ['wait', iid, '--state', 'not-a-state'])
        assert result.exit_code == 1
        assert 'Unknown state' in result.output
