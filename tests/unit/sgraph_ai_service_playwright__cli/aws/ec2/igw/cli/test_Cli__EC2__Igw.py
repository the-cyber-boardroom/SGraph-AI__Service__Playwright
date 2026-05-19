# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Igw
# Tests for `sg aws ec2 igw {list,show}` via Typer CliRunner.
# Covers table + JSON modes, vpc filter, show by id, missing-igw exit-1,
# detached-IGW rendering. No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Igw import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Igw__list:

    def test_1__empty_returns_no_igw_found(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No internet gateways found' in result.output

    def test_2__list_json_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        client.seed_igw(igw_id='igw-22222222')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_3__list_filter_by_vpc(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        client.seed_igw(igw_id='igw-22222222', vpc_id='vpc-22222222')
        result = runner.invoke(app, ['list', '--vpc', 'vpc-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['igw_id'] == 'igw-11111111'

    def test_4__list_table_renders_detached_marker(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'igw-11111111' in result.output
        assert 'detached'     in result.output

    def test_5__list_json_field_set(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111',
                        state='available', tags={'Name': 'main-gw'})
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        data   = json.loads(result.output)[0]
        assert data['igw_id']     == 'igw-11111111'
        assert data['vpc_id']     == 'vpc-11111111'
        assert data['state']      == 'available'
        assert data['tags']['Name'] == 'main-gw'


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Igw__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111')
        result = runner.invoke(app, ['show', 'igw-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['igw_id'] == 'igw-11111111'
        assert data['vpc_id'] == 'vpc-11111111'

    def test_2__show_table_renders_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111', vpc_id='vpc-11111111',
                        state='available')
        result = runner.invoke(app, ['show', 'igw-11111111'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'igw-11111111' in result.output
        assert 'vpc-11111111' in result.output
        assert 'available'    in result.output

    def test_3__show_nonexistent_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'igw-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_4__show_detached_renders_detached_marker(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_igw(igw_id='igw-11111111')
        result = runner.invoke(app, ['show', 'igw-11111111'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'detached' in result.output
