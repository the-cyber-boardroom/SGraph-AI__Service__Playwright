# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client ENI methods (list_enis, describe_network_interface)
# In-memory backed; covers sg/vpc filters, by-id resolution, field parsing,
# missing ENI returns None.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__ENI import Schema__EC2__ENI
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_enis:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        enis   = client.list_enis()
        assert enis == []

    def test_2__list_all_returns_all_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111')
        client.seed_eni(eni_id='eni-22222222')
        enis = client.list_enis()
        assert len(enis) == 2

    def test_3__sg_filter_returns_matching_only(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        client.seed_eni(eni_id='eni-22222222', sg_ids=['sg-bbbbbbbb'])
        enis = client.list_enis(sg_id='sg-aaaaaaaa')
        assert len(enis) == 1
        assert enis[0].eni_id == 'eni-11111111'

    def test_4__vpc_filter_returns_matching_only(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', vpc_id='vpc-aaaaaaaa')
        client.seed_eni(eni_id='eni-22222222', vpc_id='vpc-bbbbbbbb')
        enis = client.list_enis(vpc_id='vpc-aaaaaaaa')
        assert len(enis) == 1
        assert enis[0].eni_id == 'eni-11111111'

    def test_5__sg_and_vpc_combined_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'], vpc_id='vpc-aaaaaaaa')
        client.seed_eni(eni_id='eni-22222222', sg_ids=['sg-aaaaaaaa'], vpc_id='vpc-bbbbbbbb')
        client.seed_eni(eni_id='eni-33333333', sg_ids=['sg-bbbbbbbb'], vpc_id='vpc-aaaaaaaa')
        enis = client.list_enis(sg_id='sg-aaaaaaaa', vpc_id='vpc-aaaaaaaa')
        assert len(enis) == 1
        assert enis[0].eni_id == 'eni-11111111'

    def test_6__returns_schema_ec2_eni_objects(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111')
        enis = client.list_enis()
        assert len(enis) == 1
        assert isinstance(enis[0], Schema__EC2__ENI)

    def test_7__fields_parsed_correctly(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111',
                        subnet_id='subnet-aaa',
                        vpc_id='vpc-aaaaaaaa',
                        public_ip='1.2.3.4',
                        private_ip='10.0.0.5',
                        sg_ids=['sg-aaaaaaaa'],
                        instance_id='i-12345678',
                        attachment_status='attached',
                        status='in-use',
                        description='my-eni')
        enis = client.list_enis()
        eni  = enis[0]
        assert eni.eni_id                 == 'eni-11111111'
        assert eni.subnet_id              == 'subnet-aaa'
        assert eni.vpc_id                 == 'vpc-aaaaaaaa'
        assert eni.public_ip              == '1.2.3.4'
        assert eni.private_ip             == '10.0.0.5'
        assert eni.attachment_instance_id == 'i-12345678'
        assert eni.attachment_status      == 'attached'
        assert eni.status                 == 'in-use'
        assert eni.description            == 'my-eni'
        assert 'sg-aaaaaaaa'              in eni.security_group_ids


class Test__EC2__AWS__Client__describe_network_interface:

    def test_1__returns_schema_ec2_eni_for_known_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', vpc_id='vpc-aaaaaaaa',
                        private_ip='10.0.0.1')
        eni = client.describe_network_interface('eni-11111111')
        assert eni is not None
        assert isinstance(eni, Schema__EC2__ENI)
        assert eni.eni_id    == 'eni-11111111'
        assert eni.vpc_id    == 'vpc-aaaaaaaa'
        assert eni.private_ip== '10.0.0.1'

    def test_2__returns_none_for_unknown_id(self):
        client = EC2__AWS__Client__In_Memory()
        eni    = client.describe_network_interface('eni-deadbeef')
        assert eni is None

    def test_3__public_ip_populated_from_association(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111', public_ip='5.6.7.8')
        eni = client.describe_network_interface('eni-11111111')
        assert eni is not None
        assert eni.public_ip == '5.6.7.8'

    def test_4__security_group_ids_populated(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_eni(eni_id='eni-11111111',
                        sg_ids=['sg-aaaaaaaa', 'sg-bbbbbbbb'])
        eni = client.describe_network_interface('eni-11111111')
        assert eni is not None
        assert set(eni.security_group_ids) == {'sg-aaaaaaaa', 'sg-bbbbbbbb'}
