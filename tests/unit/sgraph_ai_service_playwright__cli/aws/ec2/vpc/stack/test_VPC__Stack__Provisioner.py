# ═══════════════════════════════════════════════════════════════════════════════
# Tests — VPC__Stack__Provisioner
# Slice 3 orchestrator. Verifies happy path, idempotent re-run, rollback on
# simulated phase failure, delete_stack, CIDR derivation, SG naming.
# In-memory EC2 client only. No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status     import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__VPC__Stack__Phase          import Enum__VPC__Stack__Phase
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Ingress_Rule import Schema__VPC__Stack__Ingress_Rule
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__VPC__Stack__Request    import Schema__VPC__Stack__Request
from sgraph_ai_service_playwright__cli.aws.ec2.service.VPC__Stack__Provisioner       import VPC__Stack__Provisioner
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


def _client_with(stack_name='example'):
    return EC2__AWS__Client__In_Memory()


def _request(stack_name='example', cidr='10.0.0.0/16'):
    return Schema__VPC__Stack__Request(stack_name=stack_name, cidr=cidr)


class Test__create_stack__happy_path:

    def test_1__all_phases_fire(self):
        provisioner = VPC__Stack__Provisioner(ec2_client=_client_with())
        report = provisioner.create_stack(_request())
        names_in_order = [p.name for p in report.phases]
        assert names_in_order == [p.value for p in Enum__VPC__Stack__Phase]

    def test_2__report_marks_ok(self):
        provisioner = VPC__Stack__Provisioner(ec2_client=_client_with())
        report = provisioner.create_stack(_request())
        assert report.ok is True
        assert report.error == ''
        assert list(report.rollback_errors) == []

    def test_3__creates_expected_resource_ids(self):
        provisioner = VPC__Stack__Provisioner(ec2_client=_client_with())
        report = provisioner.create_stack(_request())
        assert report.vpc_id              == 'vpc-00000001'
        assert report.internet_gateway_id == 'igw-00000001'
        assert report.route_table_id      == 'rtb-00000001'
        assert report.security_group_id   == 'sg-00000001'
        assert list(report.subnet_ids)    == ['subnet-00000001', 'subnet-00000002']

    def test_4__resources_tagged_with_stack_name(self):
        client = _client_with()
        VPC__Stack__Provisioner(ec2_client=client).create_stack(_request('my-stack'))
        # VPC tagged
        vpc_raw = list(client._vpcs_store.values())[0]
        vpc_tags = {t['Key']: t['Value'] for t in vpc_raw['Tags']}
        assert vpc_tags.get('Stack') == 'my-stack'

    def test_5__subnets_tagged_with_index_and_type(self):
        client = _client_with()
        VPC__Stack__Provisioner(ec2_client=client).create_stack(_request('s2'))
        for i, sub_raw in enumerate(client._subnets_store.values()):
            tags = {t['Key']: t['Value'] for t in sub_raw['Tags']}
            assert tags.get('Stack')        == 's2'
            assert tags.get('Subnet__Type') == 'public'
            assert tags.get('Subnet__Index') in {'0', '1'}

    def test_6__route_0_0_0_0_to_igw_present(self):
        client = _client_with()
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        rtb_raw = client._route_tables_store[report.route_table_id]
        routes = [r.get('DestinationCidrBlock') for r in rtb_raw['Routes']]
        assert '0.0.0.0/0' in routes

    def test_7__subnets_have_map_public_ip_on_launch(self):
        client = _client_with()
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        for sid in report.subnet_ids:
            assert client._subnets_store[sid]['MapPublicIpOnLaunch'] is True

    def test_8__sg_name_does_not_start_with_sg_dash(self):
        client = _client_with()
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request('mystack'))
        sg_raw = client._security_groups_store[report.security_group_id]
        assert sg_raw['GroupName'] == 'mystack-sg'
        assert not sg_raw['GroupName'].startswith('sg-')

    def test_9__sg_has_default_ingress_rules(self):
        client = _client_with()
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        sg_raw = client._security_groups_store[report.security_group_id]
        ports  = sorted(p['FromPort'] for p in sg_raw['IpPermissions'])
        assert ports == [80, 443, 8080]

    def test_10__total_ms_is_present(self):
        provisioner = VPC__Stack__Provisioner(ec2_client=_client_with())
        report = provisioner.create_stack(_request())
        assert report.total_ms >= 0

    def test_11__operation_is_create(self):
        provisioner = VPC__Stack__Provisioner(ec2_client=_client_with())
        report = provisioner.create_stack(_request())
        assert report.operation == 'create'


class Test__create_stack__idempotent:

    def test_1__second_run_skips_vpc(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        vpc_phase = next(p for p in r2.phases if p.name == 'VPC')
        assert vpc_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_2__second_run_skips_igw(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        igw_phase = next(p for p in r2.phases if p.name == 'INTERNET_GATEWAY')
        assert igw_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_3__second_run_skips_route_table(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        rtb_phase = next(p for p in r2.phases if p.name == 'ROUTE_TABLE')
        assert rtb_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_4__second_run_skips_route_to_igw(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        route_phase = next(p for p in r2.phases if p.name == 'ROUTE_TO_IGW')
        assert route_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_5__second_run_skips_subnets(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        sub_phase = next(p for p in r2.phases if p.name == 'SUBNETS')
        assert sub_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_6__second_run_skips_subnet_associations(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        assoc_phase = next(p for p in r2.phases if p.name == 'SUBNET_ASSOCIATIONS')
        assert assoc_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_7__second_run_skips_sg(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        sg_phase = next(p for p in r2.phases if p.name == 'SECURITY_GROUP')
        assert sg_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_8__second_run_skips_sg_ingress(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        ingr_phase = next(p for p in r2.phases if p.name == 'SG_INGRESS_RULES')
        assert ingr_phase.status == Enum__AWS__Phase__Status.SKIPPED

    def test_9__second_run_overall_ok(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        r2 = prov.create_stack(_request())
        assert r2.ok is True

    def test_10__second_run_returns_same_resource_ids(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        r1     = prov.create_stack(_request())
        r2     = prov.create_stack(_request())
        assert r1.vpc_id              == r2.vpc_id
        assert r1.internet_gateway_id == r2.internet_gateway_id
        assert r1.route_table_id      == r2.route_table_id
        assert r1.security_group_id   == r2.security_group_id
        assert list(r1.subnet_ids)    == list(r2.subnet_ids)


class _ExplodingClient(EC2__AWS__Client__In_Memory):
    # subclass that injects a forced failure into a chosen phase
    def __init__(self, *, fail_phase: str):
        super().__init__()
        self._fail_phase = fail_phase

    def authorize_security_group_ingress(self, *a, **kw):
        if self._fail_phase == 'SG_INGRESS_RULES':
            raise RuntimeError('forced failure for rollback test')
        return super().authorize_security_group_ingress(*a, **kw)


class Test__create_stack__rollback:

    def test_1__rollback_deletes_created_resources(self):
        client = _ExplodingClient(fail_phase='SG_INGRESS_RULES')
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        assert report.ok is False
        # VPC + IGW + RTB + subnets + SG all created up to the failure → all rolled back
        assert client._vpcs_store              == {}
        assert client._internet_gateways_store == {}
        assert client._route_tables_store      == {}
        assert client._subnets_store           == {}
        assert client._security_groups_store   == {}

    def test_2__report_carries_error(self):
        client = _ExplodingClient(fail_phase='SG_INGRESS_RULES')
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        assert 'forced failure' in report.error

    def test_3__rollback_errors_list_is_empty_on_clean_rollback(self):
        client = _ExplodingClient(fail_phase='SG_INGRESS_RULES')
        report = VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        assert list(report.rollback_errors) == []


class Test__delete_stack:

    def test_1__deletes_known_stack(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request('to-delete'))
        rd = prov.delete_stack('to-delete')
        assert rd.ok is True
        # All resources gone
        assert client._vpcs_store              == {}
        assert client._internet_gateways_store == {}
        assert client._route_tables_store      == {}
        assert client._subnets_store           == {}
        assert client._security_groups_store   == {}

    def test_2__delete_non_existent_stack_is_ok(self):
        client = _client_with()
        rd = VPC__Stack__Provisioner(ec2_client=client).delete_stack('never-existed')
        assert rd.ok is True

    def test_3__delete_twice_is_ok(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request())
        prov.delete_stack('example')
        rd2 = prov.delete_stack('example')
        assert rd2.ok is True

    def test_4__report_records_resource_ids(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request('x'))
        rd = prov.delete_stack('x')
        assert rd.vpc_id              == 'vpc-00000001'
        assert rd.internet_gateway_id == 'igw-00000001'
        assert rd.route_table_id      == 'rtb-00000001'
        assert rd.security_group_id   == 'sg-00000001'

    def test_5__operation_is_delete(self):
        client = _client_with()
        VPC__Stack__Provisioner(ec2_client=client).create_stack(_request())
        rd = VPC__Stack__Provisioner(ec2_client=client).delete_stack('example')
        assert rd.operation == 'delete'


class Test__describe_stack:

    def test_1__none_when_no_stack(self):
        client = _client_with()
        d = VPC__Stack__Provisioner(ec2_client=client).describe_stack('nope')
        assert d is None

    def test_2__returns_detail_after_create(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        prov.create_stack(_request('shown'))
        d = prov.describe_stack('shown')
        assert d is not None
        assert d.stack_name        == 'shown'
        assert d.vpc_id            == 'vpc-00000001'
        assert list(d.subnet_ids)  == ['subnet-00000001', 'subnet-00000002']
        assert d.security_group_id == 'sg-00000001'

    def test_3__subnet_ids_are_index_sorted(self):
        client = _client_with()
        # Seed in reverse index order to make sure describe sorts.
        client.seed_vpc(vpc_id='vpc-aaa', cidr='10.0.0.0/16',
                         tags={'Stack': 'sorted', 'Name': 'sorted-vpc'})
        client.seed_subnet(subnet_id='subnet-bbb', vpc_id='vpc-aaa',
                            cidr='10.0.16.0/20', az='eu-west-2b',
                            tags={'Stack': 'sorted', 'Subnet__Index': '1'})
        client.seed_subnet(subnet_id='subnet-aaa', vpc_id='vpc-aaa',
                            cidr='10.0.0.0/20', az='eu-west-2a',
                            tags={'Stack': 'sorted', 'Subnet__Index': '0'})
        d = VPC__Stack__Provisioner(ec2_client=client).describe_stack('sorted')
        assert list(d.subnet_ids) == ['subnet-aaa', 'subnet-bbb']


class Test__derive_subnet_cidrs:

    def test_1__defaults_for_10_0_0_0_16(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        cidrs = prov._derive_subnet_cidrs('10.0.0.0/16', 2)
        assert cidrs == ['10.0.0.0/20', '10.0.16.0/20']

    def test_2__three_subnets(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        cidrs = prov._derive_subnet_cidrs('10.0.0.0/16', 3)
        assert cidrs == ['10.0.0.0/20', '10.0.16.0/20', '10.0.32.0/20']

    def test_3__custom_cidr_192_168_0_0_24(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        cidrs = prov._derive_subnet_cidrs('192.168.0.0/24', 2)
        # /24 + 4 = /28 → 192.168.0.0/28 and 192.168.0.16/28
        assert cidrs == ['192.168.0.0/28', '192.168.0.16/28']

    def test_4__too_many_subnets_raises(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        with pytest.raises(ValueError):
            prov._derive_subnet_cidrs('10.0.0.0/30', 64)


class Test__sg_name_for_stack:

    def test_1__appends_dash_sg_suffix(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        assert prov._sg_name_for_stack('mystack') == 'mystack-sg'

    def test_2__never_starts_with_sg_dash(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        # If a caller passes a name that already starts with 'sg-' we still
        # produce a non-conflicting name.
        name = prov._sg_name_for_stack('sg-bad-name')
        assert not name.startswith('sg-')


class Test__custom_ingress_rules:

    def test_1__only_configured_ports_are_allowed(self):
        client = _client_with()
        prov   = VPC__Stack__Provisioner(ec2_client=client)
        req    = _request('custom')
        req.ingress_rules.append(Schema__VPC__Stack__Ingress_Rule(
            protocol='tcp', from_port=22, to_port=22, cidr_block='10.0.0.0/8'))
        report = prov.create_stack(req)
        sg_raw = client._security_groups_store[report.security_group_id]
        ports  = sorted(p['FromPort'] for p in sg_raw['IpPermissions'])
        assert ports == [22]


class Test__default_ingress_rules:

    def test_1__returns_three_default_rules(self):
        prov = VPC__Stack__Provisioner(ec2_client=_client_with())
        rules = prov.default_ingress_rules()
        ports = sorted(r.from_port for r in rules)
        assert ports == [80, 443, 8080]


class Test__seed_stack_helper:

    def test_1__seeds_a_complete_stack(self):
        client = _client_with()
        info   = client.seed_stack(stack_name='seeded')
        assert info['vpc_id'].startswith('vpc-')
        assert info['igw_id'].startswith('igw-')
        assert info['rtb_id'].startswith('rtb-')
        assert info['sg_id'].startswith('sg-')
        assert len(info['subnet_ids']) == 2

    def test_2__describe_stack_finds_seeded_stack(self):
        client = _client_with()
        client.seed_stack(stack_name='seeded')
        d = VPC__Stack__Provisioner(ec2_client=client).describe_stack('seeded')
        assert d is not None
        assert d.vpc_id
        assert len(d.subnet_ids) == 2
        assert d.security_group_id
