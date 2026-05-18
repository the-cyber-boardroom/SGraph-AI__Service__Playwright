# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__AWS__Client AMI methods (list_amis, describe_ami)
# In-memory backed; covers owner filters, name substring, by-id and by-name
# resolution, multi-match returns latest, missing AMI returns None.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__AWS__Client__list_amis:

    def test_1__empty_store_returns_empty(self):
        client = EC2__AWS__Client__In_Memory()
        amis   = client.list_amis()
        assert len(amis) == 0

    def test_2__owner_self_includes_seeded(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='my-image', owner='self')
        amis = client.list_amis(owner='self')
        assert len(amis) == 1
        assert str(amis[0].ami_id) == 'ami-aaaaaaaa'

    def test_3__owner_amazon_excludes_self(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='mine',   owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='public', owner='amazon')
        amis = client.list_amis(owner='amazon')
        ids  = {str(a.ami_id) for a in amis}
        assert 'ami-bbbbbbbb' in ids
        assert 'ami-aaaaaaaa' not in ids

    def test_4__owner_all_returns_all(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='mine',   owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='public', owner='amazon')
        amis = client.list_amis(owner='all')
        assert len(amis) == 2

    def test_5__name_substring_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='ubuntu-22.04', owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='al2023',       owner='self')
        amis = client.list_amis(owner='self', name_substring='ubuntu')
        ids  = {str(a.ami_id) for a in amis}
        assert ids == {'ami-aaaaaaaa'}

    def test_6__snapshot_ids_extracted_from_bdm(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='with-snap', owner='self',
                        snapshot_ids=['snap-12345678'])
        amis = client.list_amis(owner='self')
        assert len(amis) == 1
        assert [str(s) for s in amis[0].snapshot_ids] == ['snap-12345678']


class Test__EC2__AWS__Client__describe_ami:

    def test_1__by_id_returns_schema(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='direct', owner='self')
        ami = client.describe_ami('ami-aaaaaaaa')
        assert ami is not None
        assert str(ami.ami_id) == 'ami-aaaaaaaa'
        assert str(ami.name)   == 'direct'

    def test_2__by_id_missing_returns_none(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.describe_ami('ami-deadbeef') is None

    def test_3__by_name_returns_schema(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='alpha', owner='self')
        ami = client.describe_ami('alpha')
        assert ami is not None
        assert str(ami.ami_id) == 'ami-aaaaaaaa'

    def test_4__by_name_multi_match_returns_latest(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='dup',
                        owner='self', created='2026-01-01T00:00:00.000Z')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='dup',
                        owner='self', created='2026-04-01T00:00:00.000Z')
        ami = client.describe_ami('dup')
        assert ami is not None
        assert str(ami.ami_id) == 'ami-bbbbbbbb'

    def test_5__by_name_missing_returns_none(self):
        client = EC2__AWS__Client__In_Memory()
        assert client.describe_ami('no-such-name') is None
