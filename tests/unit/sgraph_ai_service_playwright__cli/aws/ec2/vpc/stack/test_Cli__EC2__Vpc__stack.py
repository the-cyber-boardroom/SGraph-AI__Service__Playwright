# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Vpc stack commands (Slice 3)
# create-stack / delete-stack / show-stack via Typer CliRunner.
# Gate-blocked path uses delenv, gate-enabled path uses setenv.
# No mocks. In-memory client injected.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Vpc import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__create_stack:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 'gated', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1
        assert len(client._vpcs_store) == 0

    def test_2__gate_enabled_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's1',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok']                  is True
        assert data['operation']           == 'create'
        assert data['stack_name']          == 's1'
        assert data['vpc_id'].startswith('vpc-')
        assert data['internet_gateway_id'].startswith('igw-')
        assert data['route_table_id'].startswith('rtb-')
        assert data['security_group_id'].startswith('sg-')
        assert len(data['subnet_ids']) == 2

    def test_3__phases_all_present_in_json(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's2',
                                      '--yes', '--json'], obj=_obj(client))
        data = json.loads(result.output)
        names = [p['name'] for p in data['phases']]
        assert 'VPC'                  in names
        assert 'INTERNET_GATEWAY'     in names
        assert 'ROUTE_TABLE'          in names
        assert 'SUBNETS'              in names
        assert 'SECURITY_GROUP'       in names
        assert 'SG_INGRESS_RULES'     in names
        assert 'TAG_PROPAGATION'      in names

    def test_4__custom_cidr_and_azs(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's3',
                                      '--cidr', '172.16.0.0/16',
                                      '--az', 'us-east-1a', '--az', 'us-east-1b',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        # Verify the AZs propagated to the seeded subnets
        azs = sorted(s['AvailabilityZone'] for s in client._subnets_store.values())
        assert azs == ['us-east-1a', 'us-east-1b']

    def test_5__custom_ingress_ports(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's4',
                                      '--ingress', '22,443',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        sg = next(iter(client._security_groups_store.values()))
        ports = sorted(p['FromPort'] for p in sg['IpPermissions'])
        assert ports == [22, 443]

    def test_6__rich_summary_on_table_output(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's5', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 0
        # Either the panel or the "stack" row should appear in the output.
        assert 's5' in result.output

    def test_7__abort_via_confirm_no(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's6'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output
        assert len(client._vpcs_store) == 0

    def test_8__time_flag_renders_phase_table(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's7',
                                      '--yes', '--time'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'Stack phases' in result.output or 'TAG_PROPAGATION' in result.output

    def test_9__invalid_ingress_port_raises(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's8',
                                      '--ingress', 'notaport',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code != 0

    def test_10__ingress_with_protocol_and_cidr(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['create-stack', '--name', 's9',
                                      '--ingress', '22/tcp@10.0.0.0/8',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        sg = next(iter(client._security_groups_store.values()))
        rule = sg['IpPermissions'][0]
        assert rule['FromPort']                == 22
        assert rule['IpProtocol']              == 'tcp'
        assert rule['IpRanges'][0]['CidrIp']   == '10.0.0.0/8'


class Test__delete_stack:

    def test_1__gate_blocked(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='to-del')
        result = runner.invoke(app, ['delete-stack', 'to-del', '--yes'],
                                obj=_obj(client))
        assert result.exit_code == 1
        assert client._vpcs_store                                                  # nothing was deleted

    def test_2__deletes_existing_stack(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='to-del')
        result = runner.invoke(app, ['delete-stack', 'to-del',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok'] is True
        assert client._vpcs_store == {}

    def test_3__delete_non_existent_is_ok(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['delete-stack', 'no-such',
                                      '--yes', '--json'], obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ok'] is True

    def test_4__abort_via_confirm_no(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='keep')
        result = runner.invoke(app, ['delete-stack', 'keep'],
                                obj=_obj(client), input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output
        assert client._vpcs_store                                                  # still there

    def test_5__operation_is_delete(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='d')
        result = runner.invoke(app, ['delete-stack', 'd',
                                      '--yes', '--json'], obj=_obj(client))
        data = json.loads(result.output)
        assert data['operation'] == 'delete'


class Test__show_stack:

    def test_1__not_found_exit_code(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show-stack', 'never'], obj=_obj(client))
        assert result.exit_code == 1

    def test_2__not_found_json(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show-stack', 'never', '--json'],
                                obj=_obj(client))
        data = json.loads(result.output)
        assert data['found'] is False

    def test_3__found_json_after_seed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='visible')
        result = runner.invoke(app, ['show-stack', 'visible', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['found']             is True
        assert data['vpc_id']
        assert data['internet_gateway_id']
        assert data['security_group_id']
        assert len(data['subnet_ids']) == 2

    def test_4__rich_table_output(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='visible')
        result = runner.invoke(app, ['show-stack', 'visible'], obj=_obj(client))
        assert result.exit_code == 0
        assert 'visible' in result.output

    def test_5__no_gate_required_for_show(self, monkeypatch):
        # show-stack is read-only — must NOT require the mutation gate
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_stack(stack_name='visible')
        result = runner.invoke(app, ['show-stack', 'visible', '--json'],
                                obj=_obj(client))
        assert result.exit_code == 0
