# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client SG methods (list_security_groups, describe_security_group)
# In-memory backed; covers vpc / name filters, by-id and by-name resolution,
# ambiguity raises ValueError, missing SG returns None, attached ENI/instance
# IDs populated correctly.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_security_groups:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        sgs    = client.list_security_groups()
        assert len(sgs) == 0

    def test_2__lists_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web',  vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='db',   vpc_id='vpc-aaaaaaaa')
        sgs = client.list_security_groups()
        ids = {str(s.sg_id) for s in sgs}
        assert ids == {'sg-aaaaaaaa', 'sg-bbbbbbbb'}

    def test_3__vpc_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='web', vpc_id='vpc-bbbbbbbb')
        sgs = client.list_security_groups(vpc_id='vpc-aaaaaaaa')
        ids = {str(s.sg_id) for s in sgs}
        assert ids == {'sg-aaaaaaaa'}

    def test_4__name_substring_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web-prod')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='db-prod')
        sgs = client.list_security_groups(name_substring='web')
        ids = {str(s.sg_id) for s in sgs}
        assert ids == {'sg-aaaaaaaa'}

    def test_5__attached_lists_empty_in_list_view(self):                          # list view skips ENI scan for speed
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web')
        client.seed_network_interface(eni_id='eni-12345678',
                                       sg_ids=['sg-aaaaaaaa'],
                                       instance_id='i-12345678')
        sgs = client.list_security_groups()
        assert len(sgs) == 1
        assert list(sgs[0].attached_eni_ids)      == []
        assert list(sgs[0].attached_instance_ids) == []

    def test_6__ingress_egress_rules_parsed(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='web',
                                    ingress=[{
                                        'IpProtocol': 'tcp',
                                        'FromPort'  : 22,
                                        'ToPort'    : 22,
                                        'IpRanges'  : [{'CidrIp': '0.0.0.0/0', 'Description': 'ssh'}],
                                    }],
                                    egress=[{
                                        'IpProtocol': '-1',
                                        'IpRanges'  : [{'CidrIp': '0.0.0.0/0'}],
                                    }])
        sgs = client.list_security_groups()
        sg  = sgs[0]
        assert len(sg.ingress_rules) == 1
        assert sg.ingress_rules[0].ip_protocol == 'tcp'
        assert sg.ingress_rules[0].from_port   == 22
        assert sg.ingress_rules[0].cidr_ipv4   == '0.0.0.0/0'
        assert len(sg.egress_rules) == 1
        assert sg.egress_rules[0].ip_protocol == '-1'


class Test__EC2__AWS__Client__describe_security_group:

    def test_1__by_id_returns_schema(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='direct')
        sg = client.describe_security_group('sg-aaaaaaaa')
        assert sg is not None
        assert str(sg.sg_id) == 'sg-aaaaaaaa'
        assert str(sg.name)  == 'direct'

    def test_2__by_id_missing_returns_none(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.describe_security_group('sg-deadbeef') is None

    def test_3__by_name_returns_schema(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='alpha', vpc_id='vpc-aaaaaaaa')
        sg = client.describe_security_group('alpha')
        assert sg is not None
        assert str(sg.sg_id) == 'sg-aaaaaaaa'

    def test_4__by_name_missing_returns_none(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.describe_security_group('no-such-name') is None

    def test_5__by_name_ambiguous_raises(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='shared', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='shared', vpc_id='vpc-bbbbbbbb')
        with pytest.raises(ValueError) as exc:
            client.describe_security_group('shared')
        assert 'Ambiguous' in str(exc.value)

    def test_6__by_name_with_vpc_disambiguates(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='shared', vpc_id='vpc-aaaaaaaa')
        client.seed_security_group(sg_id='sg-bbbbbbbb', name='shared', vpc_id='vpc-bbbbbbbb')
        sg = client.describe_security_group('shared', vpc_id='vpc-bbbbbbbb')
        assert sg is not None
        assert str(sg.sg_id) == 'sg-bbbbbbbb'

    def test_7__attached_eni_and_instance_populated(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='live')
        client.seed_network_interface(eni_id='eni-11111111',
                                       sg_ids=['sg-aaaaaaaa'],
                                       instance_id='i-12345678')
        client.seed_network_interface(eni_id='eni-22222222',
                                       sg_ids=['sg-aaaaaaaa'])                      # no instance attachment
        sg = client.describe_security_group('sg-aaaaaaaa')
        assert sg is not None
        eni_ids      = {str(e) for e in sg.attached_eni_ids}
        instance_ids = {str(i) for i in sg.attached_instance_ids}
        assert eni_ids      == {'eni-11111111', 'eni-22222222'}
        assert instance_ids == {'i-12345678'}

    def test_8__attached_lists_empty_when_no_enis(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_security_group(sg_id='sg-aaaaaaaa', name='lonely')
        sg = client.describe_security_group('sg-aaaaaaaa')
        assert sg is not None
        assert list(sg.attached_eni_ids)      == []
        assert list(sg.attached_instance_ids) == []
