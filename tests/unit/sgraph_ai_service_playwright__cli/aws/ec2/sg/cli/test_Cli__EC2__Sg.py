# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Sg
# Tests for `sg aws ec2 sg {list,show,rules,orphans}` via Typer CliRunner.
# Covers table + JSON modes, orphan detection scenarios, default-SG skip,
# rules layout, --vpc filter, ambiguous-name error path.
# No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Sg import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Sg__list:

    def test_1__empty(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No security groups found' in result.output

    def test_2__list_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web', vpc_id='vpc-aaaaaaaa')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['sg_id']  == 'sg-aaaaaaaa'
        assert data[0]['name']   == 'web'
        assert data[0]['vpc_id'] == 'vpc-aaaaaaaa'

    def test_3__list_table_renders_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'sg-aaaaaaaa' in result.output

    def test_4__vpc_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='a', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='b', vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['list', '--vpc', 'vpc-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['sg_id'] == 'sg-aaaaaaaa'

    def test_5__name_substring(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web-prod')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='db-prod')
        result = runner.invoke(app, ['list', '--name', 'web', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['sg_id'] == 'sg-aaaaaaaa'


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Sg__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='target')
        client.seed_network_interface(eni_id='eni-11111111',
                                       sg_ids=['sg-aaaaaaaa'],
                                       instance_id='i-12345678')
        result = runner.invoke(app, ['show', 'sg-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['sg_id'] == 'sg-aaaaaaaa'
        assert data['name']  == 'target'
        assert data['attached_eni_ids']      == ['eni-11111111']
        assert data['attached_instance_ids'] == ['i-12345678']

    def test_2__show_by_name(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='by-name')
        result = runner.invoke(app, ['show', 'by-name', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['sg_id'] == 'sg-aaaaaaaa'

    def test_3__show_missing_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'sg-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_4__show_ambiguous_name_errors(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='shared', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='shared', vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['show', 'shared'], obj={'ec2_client': client})
        assert result.exit_code != 0
        assert 'ambiguous' in result.output.lower()

    def test_5__show_with_vpc_disambiguates(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='shared', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='shared', vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['show', 'shared', '--vpc', 'vpc-bbbbbbbb', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['sg_id'] == 'sg-bbbbbbbb'


# ── rules ─────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Sg__rules:

    def test_1__rules_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(
            sg_id='sg-aaaaaaaa', name='web',
            ingress=[{
                'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
                'IpRanges'  : [{'CidrIp': '0.0.0.0/0', 'Description': 'ssh'}],
            }],
            egress=[{
                'IpProtocol': '-1',
                'IpRanges'  : [{'CidrIp': '0.0.0.0/0'}],
            }])
        result = runner.invoke(app, ['rules', 'sg-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['sg_id'] == 'sg-aaaaaaaa'
        assert len(data['ingress_rules']) == 1
        assert data['ingress_rules'][0]['ip_protocol'] == 'tcp'
        assert data['ingress_rules'][0]['from_port']   == 22
        assert data['ingress_rules'][0]['direction']   == 'ingress'
        assert len(data['egress_rules']) == 1
        assert data['egress_rules'][0]['direction']    == 'egress'

    def test_2__rules_table_contains_directions(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(
            sg_id='sg-aaaaaaaa', name='web',
            ingress=[{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
                      'IpRanges' : [{'CidrIp': '0.0.0.0/0'}]}],
            egress =[{'IpProtocol': '-1', 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])
        result = runner.invoke(app, ['rules', 'sg-aaaaaaaa'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'ingress' in result.output
        assert 'egress'  in result.output

    def test_3__rules_empty_when_no_rules(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='blank')
        result = runner.invoke(app, ['rules', 'sg-aaaaaaaa'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'no rules' in result.output.lower()

    def test_4__rules_missing_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['rules', 'sg-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1


# ── orphans ───────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Sg__orphans:

    def test_1__no_orphans_when_all_attached(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        result = runner.invoke(app, ['orphans', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_2__all_orphans_when_no_enis(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='unused1')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='unused2')
        result = runner.invoke(app, ['orphans', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['sg_id'] for d in data}
        assert ids == {'sg-aaaaaaaa', 'sg-bbbbbbbb'}

    def test_3__mixed_orphans_and_attached(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='unused')
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        result = runner.invoke(app, ['orphans', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['sg_id'] for d in data}
        assert ids == {'sg-bbbbbbbb'}

    def test_4__default_sg_skipped(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='default')              # auto-created — never an orphan target
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='unused')
        result = runner.invoke(app, ['orphans', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['sg_id'] for d in data}
        assert ids == {'sg-bbbbbbbb'}

    def test_5__vpc_filter_limits_scan(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='unused-a', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='unused-b', vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['orphans', '--vpc', 'vpc-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['sg_id'] for d in data}
        assert ids == {'sg-aaaaaaaa'}

    def test_6__table_output_when_orphans(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-cccccccc', name='lonely')
        result = runner.invoke(app, ['orphans'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'sg-cccccccc' in result.output
