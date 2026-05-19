# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Sg Slice 2 mutating commands
# create / add-ingress / add-egress / remove-ingress / remove-egress.
# Gate-blocked path uses delenv. No mocks. In-memory client injected.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Sg import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__create:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--name', 'web', '--vpc', 'vpc-1',
                                      '--description', 'web tier'], obj=_obj(client))
        assert result.exit_code == 1
        assert len(client._security_groups_store) == 0

    def test_2__create_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--name', 'web', '--vpc', 'vpc-1',
                                      '--description', 'web tier', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']     is True
        assert data['name']   == 'web'
        assert data['vpc_id'] == 'vpc-1'

    def test_3__create_table(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create', '--name', 'web', '--vpc', 'vpc-1',
                                      '--description', 'web tier'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'Created' in result.output


class Test__add_ingress:

    def _setup(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        sg     = client.create_security_group(group_name='web', description='w',
                                                vpc_id='vpc-1')
        return client, str(sg.sg_id)

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        result = runner.invoke(app, ['add-ingress', 'sg-aaaaaaaa',
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__add_cidr_rule(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        result = runner.invoke(app, ['add-ingress', sg_id,
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['added'] is True

    def test_3__add_source_sg_rule(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        result = runner.invoke(app, ['add-ingress', sg_id,
                                      '--protocol', 'tcp', '--from', '5432',
                                      '--to', '5432',
                                      '--source-sg', 'sg-deadbeef', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['added'] is True

    def test_4__missing_target_exits_1(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        result = runner.invoke(app, ['add-ingress', sg_id,
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80'], obj=_obj(client))
        assert result.exit_code == 1

    def test_5__both_targets_exits_1(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        result = runner.invoke(app, ['add-ingress', sg_id,
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0',
                                      '--source-sg', 'sg-x'], obj=_obj(client))
        assert result.exit_code == 1

    def test_6__duplicate_returns_added_false(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        runner.invoke(app, ['add-ingress', sg_id, '--protocol', 'tcp',
                            '--from', '80', '--to', '80', '--cidr', '0.0.0.0/0'],
                       obj=_obj(client))
        result = runner.invoke(app, ['add-ingress', sg_id, '--protocol', 'tcp',
                                      '--from', '80', '--to', '80',
                                      '--cidr', '0.0.0.0/0', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['added'] is False


class Test__add_egress:

    def _setup(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        sg     = client.create_security_group(group_name='web', description='w',
                                                vpc_id='vpc-1')
        return client, str(sg.sg_id)

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        result = runner.invoke(app, ['add-egress', 'sg-aaaaaaaa',
                                      '--protocol', 'tcp', '--from', '443',
                                      '--to', '443', '--cidr', '0.0.0.0/0'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__add_cidr_rule(self, monkeypatch):
        client, sg_id = self._setup(monkeypatch)
        result = runner.invoke(app, ['add-egress', sg_id,
                                      '--protocol', 'tcp', '--from', '443',
                                      '--to', '443', '--cidr', '0.0.0.0/0', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['added'] is True


class Test__remove_ingress:

    def _setup_with_rule(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        sg     = client.create_security_group(group_name='web', description='w',
                                                vpc_id='vpc-1')
        sg_id  = str(sg.sg_id)
        client.authorize_security_group_ingress(sg_id, 'tcp', 80, 80,
                                                  cidr_blocks=['0.0.0.0/0'])
        return client, sg_id

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        result = runner.invoke(app, ['remove-ingress', 'sg-aaaaaaaa',
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__remove_yes(self, monkeypatch):
        client, sg_id = self._setup_with_rule(monkeypatch)
        result = runner.invoke(app, ['remove-ingress', sg_id,
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['removed'] is True

    def test_3__missing_rule_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        sg     = client.create_security_group(group_name='web', description='w',
                                                vpc_id='vpc-1')
        result = runner.invoke(app, ['remove-ingress', str(sg.sg_id),
                                      '--protocol', 'tcp', '--from', '80',
                                      '--to', '80', '--cidr', '0.0.0.0/0', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1


class Test__remove_egress:

    def _setup_with_rule(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        sg     = client.create_security_group(group_name='web', description='w',
                                                vpc_id='vpc-1')
        sg_id  = str(sg.sg_id)
        client.authorize_security_group_egress(sg_id, 'tcp', 443, 443,
                                                  cidr_blocks=['0.0.0.0/0'])
        return client, sg_id

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        result = runner.invoke(app, ['remove-egress', 'sg-aaaaaaaa',
                                      '--protocol', 'tcp', '--from', '443',
                                      '--to', '443', '--cidr', '0.0.0.0/0', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1

    def test_2__remove_yes(self, monkeypatch):
        client, sg_id = self._setup_with_rule(monkeypatch)
        result = runner.invoke(app, ['remove-egress', sg_id,
                                      '--protocol', 'tcp', '--from', '443',
                                      '--to', '443', '--cidr', '0.0.0.0/0',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['removed'] is True

    def test_3__abort_via_input_no(self, monkeypatch):
        client, sg_id = self._setup_with_rule(monkeypatch)
        result = runner.invoke(app, ['remove-egress', sg_id,
                                      '--protocol', 'tcp', '--from', '443',
                                      '--to', '443', '--cidr', '0.0.0.0/0'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output
