# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Eni
# Tests for `sg aws ec2 eni {list,show}` via Typer CliRunner.
# Covers table + JSON modes, sg/vpc filters, show by id, missing-eni exit-1.
# No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Eni import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Eni__list:

    def test_1__empty_returns_no_interfaces_found(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No network interfaces found' in result.output

    def test_2__list_json_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', subnet_id='subnet-aaa',
                        vpc_id='vpc-aaaaaaaa', private_ip='10.0.0.1',
                        public_ip='1.2.3.4')
        client.seed_eni(eni_id='eni-22222222', subnet_id='subnet-bbb',
                        vpc_id='vpc-bbbbbbbb', private_ip='10.0.0.2')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        ids = {d['eni_id'] for d in data}
        assert ids == {'eni-11111111', 'eni-22222222'}

    def test_3__list_sg_filter_returns_matching_only(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        client.seed_eni(eni_id='eni-22222222', sg_ids=['sg-bbbbbbbb'])
        result = runner.invoke(app, ['list', '--sg', 'sg-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['eni_id'] == 'eni-11111111'

    def test_4__list_vpc_filter_returns_matching_only(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', vpc_id='vpc-aaaaaaaa')
        client.seed_eni(eni_id='eni-22222222', vpc_id='vpc-bbbbbbbb')
        result = runner.invoke(app, ['list', '--vpc', 'vpc-aaaaaaaa', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['eni_id'] == 'eni-11111111'

    def test_5__list_json_contains_all_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111',
                        subnet_id='subnet-aaa',
                        vpc_id='vpc-aaaaaaaa',
                        public_ip='5.6.7.8',
                        private_ip='10.10.10.10',
                        sg_ids=['sg-aaaaaaaa'],
                        instance_id='i-12345678',
                        status='in-use',
                        description='test-eni')
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data   = json.loads(result.output)
        assert len(data) == 1
        rec = data[0]
        assert rec['eni_id']                 == 'eni-11111111'
        assert rec['subnet_id']              == 'subnet-aaa'
        assert rec['vpc_id']                 == 'vpc-aaaaaaaa'
        assert rec['public_ip']              == '5.6.7.8'
        assert rec['private_ip']             == '10.10.10.10'
        assert rec['security_group_ids']     == ['sg-aaaaaaaa']
        assert rec['attachment_instance_id'] == 'i-12345678'
        assert rec['status']                 == 'in-use'
        assert rec['description']            == 'test-eni'

    def test_6__list_table_renders_eni_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', vpc_id='vpc-aaaaaaaa')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'eni-11111111' in result.output


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Eni__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111',
                        subnet_id='subnet-aaa',
                        vpc_id='vpc-aaaaaaaa',
                        public_ip='1.2.3.4',
                        private_ip='10.0.0.1',
                        sg_ids=['sg-aaaaaaaa'],
                        status='in-use')
        result = runner.invoke(app, ['show', 'eni-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['eni_id']    == 'eni-11111111'
        assert data['subnet_id'] == 'subnet-aaa'
        assert data['vpc_id']    == 'vpc-aaaaaaaa'
        assert data['public_ip'] == '1.2.3.4'
        assert data['private_ip']== '10.0.0.1'
        assert data['status']    == 'in-use'

    def test_2__show_json_security_group_ids_present(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa', 'sg-bbbbbbbb'])
        result = runner.invoke(app, ['show', 'eni-11111111', '--json'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data['security_group_ids']) == {'sg-aaaaaaaa', 'sg-bbbbbbbb'}

    def test_3__show_table_output_renders_fields(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', vpc_id='vpc-aaaaaaaa',
                        private_ip='10.0.0.5')
        result = runner.invoke(app, ['show', 'eni-11111111'],
                                obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'eni-11111111'   in result.output
        assert 'vpc-aaaaaaaa'   in result.output
        assert '10.0.0.5'       in result.output

    def test_4__show_nonexistent_prints_error_and_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'eni-deadbeef'],
                                obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()
