# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Route_Table
# Tests for `sg aws ec2 route-table {list,show}` via Typer CliRunner.
# Covers table + JSON modes, vpc filter, route/association rendering,
# missing-rtb exit-1. No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Route_Table import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Route_Table__list:

    def test_1__empty_returns_no_route_tables_found(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No route tables found' in result.output

    def test_2__list_json_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111')
        client.seed_route_table(rtb_id='rtb-22222222')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_3__list_filter_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        client.seed_route_table(rtb_id='rtb-22222222', vpc_id='vpc-22222222')
        result = runner.invoke(app, ['list', '--vpc', 'vpc-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['route_table_id'] == 'rtb-11111111'

    def test_4__list_json_renders_routes_and_associations(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 routes=[{'destination_cidr':'0.0.0.0/0',
                                          'gateway_id':'igw-12345678'}],
                                 associations=[{'association_id':'rtbassoc-1',
                                                'subnet_id':'subnet-aaaaaaaa'}])
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        data   = json.loads(result.output)[0]
        assert len(data['routes'])       == 1
        assert data['routes'][0]['gateway_id']  == 'igw-12345678'
        assert len(data['associations']) == 1
        assert data['associations'][0]['subnet_id'] == 'subnet-aaaaaaaa'

    def test_5__list_table_renders_rtb_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'rtb-11111111' in result.output


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Route_Table__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['show', 'rtb-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['route_table_id'] == 'rtb-11111111'
        assert data['vpc_id']         == 'vpc-11111111'

    def test_2__show_table_renders_routes_and_associations(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_route_table(rtb_id='rtb-11111111', vpc_id='vpc-11111111',
                                 routes=[{'destination_cidr':'10.0.0.0/16',
                                          'gateway_id':'local'},
                                         {'destination_cidr':'0.0.0.0/0',
                                          'gateway_id':'igw-aaaaaaaa'}],
                                 associations=[{'association_id':'rtbassoc-1',
                                                'subnet_id':'subnet-aaaaaaaa'}])
        result = runner.invoke(app, ['show', 'rtb-11111111'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'rtb-11111111'    in result.output
        assert '0.0.0.0/0'       in result.output
        assert 'igw-aaaaaaaa'    in result.output
        assert 'subnet-aaaaaaaa' in result.output

    def test_3__show_nonexistent_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'rtb-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()
