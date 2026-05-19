# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Subnet
# Tests for `sg aws ec2 subnet {list,show}` via Typer CliRunner.
# Covers table + JSON modes, vpc/az filters, show by id, missing-subnet exit-1.
# No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Subnet import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Subnet__list:

    def test_1__empty_returns_no_subnets_found(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No subnets found' in result.output

    def test_2__list_json_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_3__list_filtered_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', vpc_id='vpc-22222222')
        result = runner.invoke(app, ['list', '--vpc', 'vpc-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['subnet_id'] == 'subnet-aaaaaaaa'

    def test_4__list_filtered_by_az(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', az='eu-west-2a')
        client.seed_subnet(subnet_id='subnet-bbbbbbbb', az='eu-west-2b')
        result = runner.invoke(app, ['list', '--az', 'eu-west-2a', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['availability_zone'] == 'eu-west-2a'

    def test_5__list_json_field_set(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                            cidr='10.0.1.0/24', az='eu-west-2a', public=True,
                            available_ip_count=100, tags={'Tier': 'public'})
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        data   = json.loads(result.output)[0]
        assert data['subnet_id']               == 'subnet-aaaaaaaa'
        assert data['cidr_block']              == '10.0.1.0/24'
        assert data['availability_zone']       == 'eu-west-2a'
        assert data['map_public_ip_on_launch'] is True
        assert data['available_ip_count']      == 100
        assert data['tags']['Tier']            == 'public'

    def test_6__list_table_renders_title(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', cidr='10.0.1.0/24')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        # Rich may truncate cells in narrow terminals — assert the title only.
        assert 'Subnets' in result.output


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Subnet__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', vpc_id='vpc-11111111',
                            cidr='10.0.1.0/24', az='eu-west-2a')
        result = runner.invoke(app, ['show', 'subnet-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['subnet_id'] == 'subnet-aaaaaaaa'
        assert data['vpc_id']    == 'vpc-11111111'

    def test_2__show_table_renders_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_subnet(subnet_id='subnet-aaaaaaaa', az='eu-west-2b')
        result = runner.invoke(app, ['show', 'subnet-aaaaaaaa'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'subnet-aaaaaaaa' in result.output
        assert 'eu-west-2b'      in result.output

    def test_3__show_nonexistent_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'subnet-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()
