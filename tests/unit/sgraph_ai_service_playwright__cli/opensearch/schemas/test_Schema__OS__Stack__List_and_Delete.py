# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__OS__Stack__List + Schema__OS__Stack__Delete__Response
# Two small response wrappers grouped in one file since neither warrants its own.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.collections.List__Schema__OS__Stack__Info import List__Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Delete__Response import Schema__OS__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__List   import Schema__OS__Stack__List


class test_Schema__OS__Stack__List(TestCase):

    def test__defaults(self):
        listing = Schema__OS__Stack__List()
        assert str(listing.region)    == ''
        assert list(listing.stacks)   == []

    def test__round_trip_with_two_stacks(self):
        a = Schema__OS__Stack__Info(stack_name='os-aaa', instance_id='i-0123456789abcdef0')
        b = Schema__OS__Stack__Info(stack_name='os-bbb', instance_id='i-0123456789abcdef1')
        listing = Schema__OS__Stack__List(region='eu-west-2', stacks=List__Schema__OS__Stack__Info([a, b]))
        again   = Schema__OS__Stack__List.from_json(listing.json())
        assert str(again.region)             == 'eu-west-2'
        assert len(again.stacks)             == 2
        assert str(again.stacks[0].stack_name) == 'os-aaa'


class test_Schema__OS__Stack__Delete__Response(TestCase):

    def test__defaults_are_empty(self):                                             # Empty fields ⇒ route returns 404
        resp = Schema__OS__Stack__Delete__Response()
        assert str(resp.target)                  == ''
        assert str(resp.stack_name)              == ''
        assert list(resp.terminated_instance_ids) == []

    def test__round_trip_with_terminated(self):
        from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id import List__Instance__Id
        ids = List__Instance__Id()
        ids.append('i-0123456789abcdef0')
        resp  = Schema__OS__Stack__Delete__Response(target='i-0123456789abcdef0',
                                                     stack_name='os-quiet-fermi',
                                                     terminated_instance_ids=ids)
        again = Schema__OS__Stack__Delete__Response.from_json(resp.json())
        assert str(again.target)                  == 'i-0123456789abcdef0'
        assert str(again.stack_name)              == 'os-quiet-fermi'
        assert [str(iid) for iid in again.terminated_instance_ids] == ['i-0123456789abcdef0']
