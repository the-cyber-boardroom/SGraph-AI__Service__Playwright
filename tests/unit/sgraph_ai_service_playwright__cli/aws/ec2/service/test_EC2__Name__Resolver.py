# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2__Name__Resolver (in-memory)
# Tests name-based lookup, ID pass-through, and ambiguity errors.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__Name__Resolver import EC2__Name__Resolver
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


class Test__EC2__Name__Resolver:

    def test_1__resolve_instance_id_direct(self):
        client   = EC2__AWS__Client__In_Memory()
        iid      = client.seed_instance(name='alpha')
        resolver = EC2__Name__Resolver(ec2_client=client)
        result   = resolver.resolve(iid)
        assert result == iid                                                    # ID returned as-is

    def test_2__resolve_by_name(self):
        client   = EC2__AWS__Client__In_Memory()
        iid      = client.seed_instance(name='my-server')
        resolver = EC2__Name__Resolver(ec2_client=client)
        result   = resolver.resolve('my-server')
        assert result == iid

    def test_3__resolve_missing_raises(self):
        client   = EC2__AWS__Client__In_Memory()
        resolver = EC2__Name__Resolver(ec2_client=client)
        with pytest.raises(ValueError, match='No instance found'):
            resolver.resolve('no-such-name')

    def test_4__resolve_ambiguous_raises_with_ids(self):
        client = EC2__AWS__Client__In_Memory()
        iid1   = client.seed_instance(name='dev-server')
        iid2   = client.seed_instance(name='dev-server')
        resolver = EC2__Name__Resolver(ec2_client=client)
        with pytest.raises(ValueError, match='Ambiguous'):
            resolver.resolve('dev-server')

    def test_5__resolve_by_name_prefix(self):
        client = EC2__AWS__Client__In_Memory()
        iid    = client.seed_instance(name='prefix-server-abc')
        resolver = EC2__Name__Resolver(ec2_client=client)
        result = resolver.resolve('prefix-server')
        assert result == iid
