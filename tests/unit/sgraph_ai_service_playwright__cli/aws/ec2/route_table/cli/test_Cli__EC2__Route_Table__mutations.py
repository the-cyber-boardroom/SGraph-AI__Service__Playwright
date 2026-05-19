# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Route_Table mutating commands
# create / delete / add-route / remove-route / associate / disassociate.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Route_Table import app
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
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__create_yes_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['create', '--vpc', 'vpc-11111111',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']             is True
        assert data['vpc_id']         == 'vpc-11111111'
        assert data['route_table_id'].startswith('rtb-')


class Test__delete:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'rtb-11111111', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__delete_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['delete', 'rtb-11111111', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deleted'] is True

    def test_3__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['delete', 'rtb-deadbeef', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1


class Test__add_route:

    def _setup(self):
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        return client

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = self._setup()
        result = runner.invoke(app, ['add-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0',
                                      '--igw', 'igw-11111111'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__add_via_igw_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = self._setup()
        result = runner.invoke(app, ['add-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0',
                                      '--igw', 'igw-11111111',
                                      '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']               is True
        assert data['destination_cidr'] == '0.0.0.0/0'
        assert data['gateway_id']       == 'igw-11111111'

    def test_3__no_target_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = self._setup()
        result = runner.invoke(app, ['add-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0'], obj=_obj(client))
        assert result.exit_code == 1
        assert 'exactly one target' in result.output.lower()

    def test_4__multiple_targets_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = self._setup()
        result = runner.invoke(app, ['add-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0',
                                      '--igw', 'igw-1', '--nat', 'nat-1'],
                                obj=_obj(client))
        assert result.exit_code == 1


class Test__remove_route:

    def _setup(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        client.create_route('rtb-11111111', destination_cidr='0.0.0.0/0',
                             gateway_id='igw-11111111')
        return client

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['remove-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__remove_yes_json(self, monkeypatch):
        client = self._setup(monkeypatch)
        result = runner.invoke(app, ['remove-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['removed'] is True

    def test_3__remove_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['remove-route', 'rtb-11111111',
                                      '--cidr', '0.0.0.0/0', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1


class Test__associate:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['associate', 'rtb-11111111',
                                      '--subnet', 'subnet-aaaaaaaa'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__associate_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['associate', 'rtb-11111111',
                                      '--subnet', 'subnet-aaaaaaaa', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['association_id'].startswith('rtbassoc-')


class Test__disassociate:

    def _setup(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        assoc  = client.associate_route_table('rtb-11111111', 'subnet-aaaaaaaa')
        return client, assoc

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = _client_with_vpc()
        result = runner.invoke(app, ['disassociate', 'rtbassoc-x', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__disassociate_yes(self, monkeypatch):
        client, assoc = self._setup(monkeypatch)
        result = runner.invoke(app, ['disassociate', assoc, '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['disassociated'] is True

    def test_3__disassociate_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = _client_with_vpc()
        result = runner.invoke(app, ['disassociate', 'rtbassoc-deadbeef',
                                      '--yes'], obj=_obj(client))
        assert result.exit_code == 1
