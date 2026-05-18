# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client.list_network_interfaces
# Covers ENI filter by sg_id: empty / one / many.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_network_interfaces:

    def test_1__empty_when_no_enis(self):
        client = EC2__AWS__Client__In_Memory()
        enis   = client.list_network_interfaces(sg_id='sg-aaaaaaaa')
        assert enis == []

    def test_2__single_match(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        enis = client.list_network_interfaces(sg_id='sg-aaaaaaaa')
        assert len(enis) == 1
        assert enis[0]['NetworkInterfaceId'] == 'eni-11111111'

    def test_3__multiple_matches(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        client.seed_network_interface(eni_id='eni-22222222', sg_ids=['sg-aaaaaaaa'])
        client.seed_network_interface(eni_id='eni-33333333', sg_ids=['sg-bbbbbbbb'])
        enis = client.list_network_interfaces(sg_id='sg-aaaaaaaa')
        ids  = {e['NetworkInterfaceId'] for e in enis}
        assert ids == {'eni-11111111', 'eni-22222222'}

    def test_4__no_sg_filter_returns_all(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-aaaaaaaa'])
        client.seed_network_interface(eni_id='eni-22222222', sg_ids=['sg-bbbbbbbb'])
        enis = client.list_network_interfaces()
        assert len(enis) == 2

    def test_5__filter_excludes_non_member_enis(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_network_interface(eni_id='eni-11111111', sg_ids=['sg-bbbbbbbb'])
        enis = client.list_network_interfaces(sg_id='sg-aaaaaaaa')
        assert enis == []
