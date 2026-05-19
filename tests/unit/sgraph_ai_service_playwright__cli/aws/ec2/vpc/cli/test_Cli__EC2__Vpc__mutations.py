# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Vpc mutating commands
# create / delete / modify-attr via Typer CliRunner. Gate-blocked path uses
# delenv, gate-enabled path uses setenv. No mocks. In-memory client injected.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Vpc import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__create:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1
        assert len(client._vpcs_store) == 0

    def test_2__create_yes_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']         is True
        assert data['vpc_id'].startswith('vpc-')
        assert data['cidr_block'] == '10.0.0.0/16'

    def test_3__create_with_name(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16',
                                      '--name', 'main', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        vpc  = client.describe_vpc(data['vpc_id'])
        assert str(vpc.tags['Name']) == 'main'

    def test_4__create_table_output(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 0
        assert 'Created' in result.output

    def test_5__abort_via_input_no(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output
        assert len(client._vpcs_store) == 0

    def test_6__abort_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16', '--json'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        # confirm prompt echoes before the JSON; extract the JSON payload tail.
        json_blob = result.output[result.output.index('{'):]
        data = json.loads(json_blob)
        assert data['ok']      is False
        assert data['aborted'] is True

    def test_7__enable_dns_flag_applies_attribute(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--cidr', '10.0.0.0/16',
                                      '--enable-dns', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        raw  = client._vpcs_store[data['vpc_id']]
        assert raw.get('EnableDnsSupport') is True


class Test__delete:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'vpc-11111111', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1
        assert client.describe_vpc('vpc-11111111') is not None

    def test_2__delete_with_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'vpc-11111111', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deleted' in result.output
        assert client.describe_vpc('vpc-11111111') is None

    def test_3__delete_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'vpc-11111111', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']      is True
        assert data['deleted'] is True

    def test_4__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['delete', 'vpc-deadbeef', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_5__abort_via_input_no(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'vpc-11111111'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output
        assert client.describe_vpc('vpc-11111111') is not None


class Test__modify_attr:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'vpc-11111111', '--enable-dns'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__enable_dns(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'vpc-11111111', '--enable-dns',
                                      '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok'] is True
        assert data['enable_dns_support'] is True

    def test_3__no_flags_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'vpc-11111111'],
                                obj=_obj(client))
        assert result.exit_code == 1
        assert 'Nothing to change' in result.output

    def test_4__only_hostnames(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'vpc-11111111',
                                      '--enable-dns-hostnames', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['enable_dns_hostnames'] is True
        # enable_dns_support must NOT be in payload — we didn't pass --enable-dns
        assert 'enable_dns_support' not in data
