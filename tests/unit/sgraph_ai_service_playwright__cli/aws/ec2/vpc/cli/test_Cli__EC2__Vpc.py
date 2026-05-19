# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Vpc
# Tests for `sg aws ec2 vpc {list,show}` via Typer CliRunner.
# Covers table + JSON modes, vpc-substring filter, show by id, missing-vpc
# exits 1. No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Vpc import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Vpc__list:

    def test_1__empty_returns_no_vpcs_found(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No VPCs found' in result.output

    def test_2__list_json_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111')
        client.seed_vpc(vpc_id='vpc-22222222')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert {d['vpc_id'] for d in data} == {'vpc-11111111', 'vpc-22222222'}

    def test_3__vpc_substring_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-aaaaaaaa')
        client.seed_vpc(vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['list', '--vpc-substring', 'aaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['vpc_id'] == 'vpc-aaaaaaaa'

    def test_4__list_json_contains_all_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.0.0.0/16',
                        is_default=True, instance_tenancy='dedicated',
                        tags={'Name': 'main'})
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        data   = json.loads(result.output)[0]
        assert data['vpc_id']           == 'vpc-11111111'
        assert data['cidr_block']       == '10.0.0.0/16'
        assert data['is_default']       is True
        assert data['instance_tenancy'] == 'dedicated'
        assert data['tags']['Name']     == 'main'

    def test_5__list_table_renders_vpc_id_and_cidr(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.0.0.0/16')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'vpc-11111111' in result.output
        assert '10.0.0.0/16'  in result.output


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Vpc__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.0.0.0/16', is_default=True)
        result = runner.invoke(app, ['show', 'vpc-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['vpc_id']     == 'vpc-11111111'
        assert data['cidr_block'] == '10.0.0.0/16'
        assert data['is_default'] is True

    def test_2__show_table_output_renders_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_vpc(vpc_id='vpc-11111111', cidr='10.0.0.0/16',
                        tags={'Name': 'main'})
        result = runner.invoke(app, ['show', 'vpc-11111111'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'vpc-11111111' in result.output
        assert '10.0.0.0/16'  in result.output
        assert 'Name=main'    in result.output

    def test_3__show_nonexistent_prints_error_and_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'vpc-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()
