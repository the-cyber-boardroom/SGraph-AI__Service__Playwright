# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Subnet mutating commands
# create / delete / modify-attr via Typer CliRunner. Gate-blocked path uses
# delenv. No mocks. In-memory client injected.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Subnet import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


def _client_with_vpc():
    c = EC2__AWS__Client__In_Memory()
    c.seed_vpc(vpc_id='vpc-11111111')
    return c


class Test__create:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--cidr', '10.0.1.0/24', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__create_yes_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--cidr', '10.0.1.0/24', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']         is True
        assert data['cidr_block'] == '10.0.1.0/24'
        assert data['vpc_id']     == 'vpc-11111111'
        assert data['public']     is False

    def test_3__create_with_public_sets_attr(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--cidr', '10.0.1.0/24', '--public',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        sub  = client.describe_subnet(data['subnet_id'])
        assert sub.map_public_ip_on_launch is True

    def test_4__create_with_az(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--cidr', '10.0.1.0/24', '--az', 'eu-west-2c',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        sub  = client.describe_subnet(data['subnet_id'])
        assert str(sub.availability_zone) == 'eu-west-2c'

    def test_5__create_table_output(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--cidr', '10.0.1.0/24', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 0
        assert 'Created' in result.output


class Test__delete:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'subnet-aaaaaaaa', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__delete_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'subnet-aaaaaaaa', '--yes',
                                      '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deleted'] is True

    def test_3__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['delete', 'subnet-deadbeef', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_4__abort(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'subnet-aaaaaaaa'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output


class Test__modify_attr:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'subnet-aaaaaaaa', '--public'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__set_public_true(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                            public=False)
        result = runner.invoke(app, ['modify-attr', 'subnet-aaaaaaaa', '--public',
                                      '--json'], obj=_obj(client))
        assert result.exit_code == 0
        sub = client.describe_subnet('subnet-aaaaaaaa')
        assert sub.map_public_ip_on_launch is True

    def test_3__set_public_false(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                            public=True)
        result = runner.invoke(app, ['modify-attr', 'subnet-aaaaaaaa',
                                      '--no-public'], obj=_obj(client))
        assert result.exit_code == 0
        sub = client.describe_subnet('subnet-aaaaaaaa')
        assert sub.map_public_ip_on_launch is False

    def test_4__no_flags_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['modify-attr', 'subnet-aaaaaaaa'],
                                obj=_obj(client))
        assert result.exit_code == 1
