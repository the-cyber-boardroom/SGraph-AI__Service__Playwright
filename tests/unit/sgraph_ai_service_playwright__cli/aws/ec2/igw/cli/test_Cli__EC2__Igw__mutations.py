# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Igw mutating commands
# create / delete / attach / detach via Typer CliRunner.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Igw import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__create:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--yes'], obj=_obj(client))
        assert result.exit_code == 1
        assert len(client._internet_gateways_store) == 0

    def test_2__create_yes_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok'] is True
        assert data['igw_id'].startswith('igw-')

    def test_3__create_with_name(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--name', 'main', '--yes', '--json'],
                                obj=_obj(client))
        data  = json.loads(result.output)
        igw   = client.describe_internet_gateway(data['igw_id'])
        assert str(igw.tags['Name']) == 'main'


class Test__delete:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['delete', 'igw-11111111', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__delete_yes(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['delete', 'igw-11111111', '--yes', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deleted'] is True

    def test_3__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['delete', 'igw-deadbeef', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1


class Test__attach:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['attach', 'igw-11111111', '--vpc', 'vpc-1'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__attach(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['attach', 'igw-11111111', '--vpc', 'vpc-aaaaaaaa',
                                      '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok'] is True
        igw = client.describe_internet_gateway('igw-11111111')
        assert str(igw.vpc_id) == 'vpc-aaaaaaaa'

    def test_3__attach_already_attached_is_noop(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-aaaaaaaa')
        result = runner.invoke(app, ['attach', 'igw-11111111', '--vpc', 'vpc-aaaaaaaa'],
                                obj=_obj(client))
        assert result.exit_code == 0


class Test__detach:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-aaaaaaaa')
        result = runner.invoke(app, ['detach', 'igw-11111111', '--vpc', 'vpc-aaaaaaaa',
                                      '--yes'], obj=_obj(client))
        assert result.exit_code == 1

    def test_2__detach_yes_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-aaaaaaaa')
        result = runner.invoke(app, ['detach', 'igw-11111111', '--vpc', 'vpc-aaaaaaaa',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['detached'] is True
        igw  = client.describe_internet_gateway('igw-11111111')
        assert str(igw.vpc_id) == ''

    def test_3__detach_not_attached_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')                                   # not attached
        result = runner.invoke(app, ['detach', 'igw-11111111', '--vpc', 'vpc-aaaaaaaa',
                                      '--yes'], obj=_obj(client))
        assert result.exit_code == 1
