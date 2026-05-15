# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__AWS__Client
# All tests run against _Fake_Route53__AWS__Client — a real subclass of
# Route53__AWS__Client that overrides client() to return an in-memory stub.
# No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest                                                                        import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Hosted_Zone import List__Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Record      import List__Schema__Route53__Record
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type               import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Change__Result        import Schema__Route53__Change__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone           import Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Record                import Schema__Route53__Record
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client                   import Route53__AWS__Client


# ── In-memory boto3 stub ──────────────────────────────────────────────────────

_FAKE_ZONES = [                                                                      # Canned hosted zone data — mirrors the boto3 ListHostedZones response shape
    {'Id'                    : '/hostedzone/Z01ABCDEFGHIJ'    ,
     'Name'                  : 'sgraph.ai.'                   ,
     'Config'                : {'Comment': 'Default', 'PrivateZone': False},
     'ResourceRecordSetCount': 12                              ,
     'CallerReference'       : 'ref-001'                      },
    {'Id'                    : '/hostedzone/Z02ZYXWVUTSRQ'    ,
     'Name'                  : 'internal.example.'            ,
     'Config'                : {'Comment': 'VPC', 'PrivateZone': True},
     'ResourceRecordSetCount': 4                               ,
     'CallerReference'       : 'ref-002'                      },
]

_FAKE_RECORDS = [                                                                    # Canned record data for sgraph.ai zone — mirrors ResourceRecordSets shape
    {'Name'            : 'sgraph.ai.'                                         ,
     'Type'            : 'NS'                                                 ,
     'TTL'             : 172800                                                ,
     'ResourceRecords' : [{'Value': 'ns-1.awsdns-1.com.'},
                           {'Value': 'ns-2.awsdns-2.net.'}]                   },
    {'Name'            : 'sgraph.ai.'                                         ,
     'Type'            : 'SOA'                                                ,
     'TTL'             : 900                                                   ,
     'ResourceRecords' : [{'Value': 'ns-1.awsdns-1.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400'}]},
    {'Name'            : 'test.sgraph.ai.'                                    ,
     'Type'            : 'A'                                                   ,
     'TTL'             : 300                                                   ,
     'ResourceRecords' : [{'Value': '203.0.113.1'}]                           },
    {'Name'            : 'www.sgraph.ai.'                                     ,
     'Type'            : 'CNAME'                                              ,
     'TTL'             : 60                                                    ,
     'ResourceRecords' : [{'Value': 'sgraph.ai.'}]                            },
]

_CANNED_CHANGE_RESPONSE = {                                                          # Canned response for change_resource_record_sets calls
    'ChangeInfo': {'Id': '/change/CFAKE123', 'Status': 'PENDING',
                   'SubmittedAt': '2026-05-15T00:00:00Z'}
}


class _Fake_Route53_Boto3_Client:                                                    # In-memory stand-in that returns canned data for the paginator calls
    def __init__(self):
        self.last_change_batch  = None                                               # Records the last change_resource_record_sets call for assertions
        self.get_change_calls   = 0                                                  # Counts get_change calls; 0/1/2/... drives the PENDING → INSYNC scripted sequence below
        self.get_change_script  = ['INSYNC']                                         # Override per test to script a longer PENDING → INSYNC sequence

    def get_paginator(self, operation):
        if operation == 'list_hosted_zones':
            return _FakePaginator([{'HostedZones': _FAKE_ZONES}])
        if operation == 'list_resource_record_sets':
            return _FakePaginator([{'ResourceRecordSets': _FAKE_RECORDS}])
        return _FakePaginator([{}])

    def get_hosted_zone(self, Id):                                                   # Used by get_hosted_zone() when an id is passed
        zone_id = Id.replace('/hostedzone/', '')
        for z in _FAKE_ZONES:
            if z['Id'].replace('/hostedzone/', '') == zone_id:
                return {'HostedZone': z, 'DelegationSet': {'NameServers': ['ns-1.awsdns-1.com']}}
        return {'HostedZone': {}}

    def change_resource_record_sets(self, HostedZoneId, ChangeBatch):               # Records the call and returns a canned PENDING response
        self.last_change_batch = ChangeBatch
        return _CANNED_CHANGE_RESPONSE

    def get_change(self, Id):                                                        # Returns the next status from get_change_script; sticky on the last element
        idx    = min(self.get_change_calls, len(self.get_change_script) - 1)
        status = self.get_change_script[idx]
        self.get_change_calls += 1
        return {'ChangeInfo': {'Id': Id, 'Status': status, 'SubmittedAt': '2026-05-15T00:00:00Z'}}


class _FakePaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        return iter(self._pages)


class _Fake_Route53__AWS__Client(Route53__AWS__Client):                              # Real subclass — overrides the boto3 seam; no mocks
    _boto3_stub : _Fake_Route53_Boto3_Client = None

    def client(self):
        if self._boto3_stub is None:
            self._boto3_stub = _Fake_Route53_Boto3_Client()
        return self._boto3_stub


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__AWS__Client(TestCase):

    def setUp(self):
        self.client = _Fake_Route53__AWS__Client()

    # ── list_hosted_zones ────────────────────────────────────────────────────

    def test__list_hosted_zones__returns_typed_list(self):
        zones = self.client.list_hosted_zones()
        assert isinstance(zones, List__Schema__Route53__Hosted_Zone)

    def test__list_hosted_zones__contains_correct_count(self):
        zones = self.client.list_hosted_zones()
        assert len(zones) == 2

    def test__list_hosted_zones__schemas_are_correct_type(self):
        zones = self.client.list_hosted_zones()
        for z in zones:
            assert isinstance(z, Schema__Route53__Hosted_Zone)

    def test__list_hosted_zones__sgraph_ai_zone_present(self):
        zones = self.client.list_hosted_zones()
        names = [str(z.name) for z in zones]
        assert 'sgraph.ai' in names                                                  # Trailing dot stripped by client

    def test__list_hosted_zones__zone_id_stripped_of_hostedzone_prefix(self):
        zones = self.client.list_hosted_zones()
        for z in zones:
            assert not str(z.zone_id).startswith('/hostedzone/')
            assert str(z.zone_id).startswith('Z')

    def test__list_hosted_zones__private_zone_flag_correct(self):
        zones    = self.client.list_hosted_zones()
        by_name  = {str(z.name): z for z in zones}
        assert by_name['sgraph.ai'].private_zone     is False
        assert by_name['internal.example'].private_zone is True

    # ── find_hosted_zone_by_name ─────────────────────────────────────────────

    def test__find_hosted_zone_by_name__returns_zone_for_sgraph_ai(self):
        zone = self.client.find_hosted_zone_by_name('sgraph.ai')
        assert zone is not None
        assert isinstance(zone, Schema__Route53__Hosted_Zone)
        assert str(zone.name) == 'sgraph.ai'

    def test__find_hosted_zone_by_name__trailing_dot_normalised(self):               # Route 53 returns names with trailing dot — both forms should match
        assert self.client.find_hosted_zone_by_name('sgraph.ai')  is not None
        assert self.client.find_hosted_zone_by_name('sgraph.ai.') is not None

    def test__find_hosted_zone_by_name__returns_none_for_nonexistent(self):
        result = self.client.find_hosted_zone_by_name('nonexistent.example')
        assert result is None

    # ── resolve_default_zone ─────────────────────────────────────────────────

    def test__resolve_default_zone__returns_sgraph_ai(self):
        zone = self.client.resolve_default_zone()
        assert zone is not None
        assert str(zone.name) == 'sgraph.ai'

    def test__resolve_default_zone__caches_on_second_call(self):
        zone1 = self.client.resolve_default_zone()
        zone2 = self.client.resolve_default_zone()
        assert zone1 is zone2                                                        # Same object — cached

    # ── list_records ─────────────────────────────────────────────────────────

    def test__list_records__returns_typed_list(self):
        zone_id = 'Z01ABCDEFGHIJ'
        records = self.client.list_records(zone_id)
        assert isinstance(records, List__Schema__Route53__Record)

    def test__list_records__contains_correct_count(self):
        records = self.client.list_records('Z01ABCDEFGHIJ')
        assert len(records) == 4

    def test__list_records__schemas_are_correct_type(self):
        for r in self.client.list_records('Z01ABCDEFGHIJ'):
            assert isinstance(r, Schema__Route53__Record)

    def test__list_records__record_type_is_enum(self):
        for r in self.client.list_records('Z01ABCDEFGHIJ'):
            assert isinstance(r.record_type, Enum__Route53__Record_Type)

    def test__list_records__ns_record_has_multiple_values(self):
        records   = self.client.list_records('Z01ABCDEFGHIJ')
        ns_record = next(r for r in records if str(r.record_type) == 'NS')
        assert len(ns_record.values) == 2

    def test__list_records__accepts_zone_name_too(self):                              # resolve_zone_id path when a name is passed
        records_by_id   = self.client.list_records('Z01ABCDEFGHIJ')
        records_by_name = self.client.list_records('sgraph.ai')
        assert len(records_by_id) == len(records_by_name)

    # ── get_record ───────────────────────────────────────────────────────────

    def test__get_record__returns_correct_a_record(self):
        record = self.client.get_record('Z01ABCDEFGHIJ', 'test.sgraph.ai', Enum__Route53__Record_Type.A)
        assert record is not None
        assert isinstance(record, Schema__Route53__Record)
        assert str(record.record_type) == 'A'
        assert '203.0.113.1' in record.values

    def test__get_record__returns_none_for_nonexistent(self):
        record = self.client.get_record('Z01ABCDEFGHIJ', 'nope.sgraph.ai', Enum__Route53__Record_Type.A)
        assert record is None

    def test__get_record__default_type_is_a(self):
        record = self.client.get_record('Z01ABCDEFGHIJ', 'test.sgraph.ai')
        assert record is not None
        assert str(record.record_type) == 'A'

    def test__get_record__trailing_dot_normalised(self):                              # Route 53 returns names with trailing dot — look up without it and still find it
        record = self.client.get_record('Z01ABCDEFGHIJ', 'test.sgraph.ai.')
        assert record is not None

    def test__get_record__cname_type_resolved(self):
        record = self.client.get_record('Z01ABCDEFGHIJ', 'www.sgraph.ai', Enum__Route53__Record_Type.CNAME)
        assert record is not None
        assert str(record.record_type) == 'CNAME'

    # ── P1: create_record ─────────────────────────────────────────────────────

    def test__create_record__returns_schema_change_result(self):
        result = self.client.create_record('Z01ABCDEFGHIJ', 'new.sgraph.ai',
                                           Enum__Route53__Record_Type.A, ['1.2.3.4'])
        assert isinstance(result, Schema__Route53__Change__Result)

    def test__create_record__change_id_is_populated(self):
        result = self.client.create_record('Z01ABCDEFGHIJ', 'new.sgraph.ai',
                                           Enum__Route53__Record_Type.A, ['1.2.3.4'])
        assert result.change_id == '/change/CFAKE123'
        assert result.status    == 'PENDING'

    def test__create_record__calls_change_rrsets_with_create_action(self):
        self.client.create_record('Z01ABCDEFGHIJ', 'new.sgraph.ai',
                                  Enum__Route53__Record_Type.A, ['1.2.3.4'])
        batch  = self.client.client().last_change_batch
        action = batch['Changes'][0]['Action']
        assert action == 'CREATE'

    def test__create_record__raises_if_record_already_exists(self):
        with pytest.raises(ValueError, match='already exists'):
            self.client.create_record('Z01ABCDEFGHIJ', 'test.sgraph.ai',
                                      Enum__Route53__Record_Type.A, ['9.9.9.9'])

    # ── P1: upsert_record ─────────────────────────────────────────────────────

    def test__upsert_record__returns_schema_change_result(self):
        result = self.client.upsert_record('Z01ABCDEFGHIJ', 'test.sgraph.ai',
                                           Enum__Route53__Record_Type.A, ['5.6.7.8'])
        assert isinstance(result, Schema__Route53__Change__Result)

    def test__upsert_record__calls_change_rrsets_with_upsert_action(self):
        self.client.upsert_record('Z01ABCDEFGHIJ', 'test.sgraph.ai',
                                  Enum__Route53__Record_Type.A, ['5.6.7.8'])
        batch  = self.client.client().last_change_batch
        action = batch['Changes'][0]['Action']
        assert action == 'UPSERT'

    # ── P1: delete_record ─────────────────────────────────────────────────────

    def test__delete_record__fetches_existing_then_calls_delete(self):
        result = self.client.delete_record('Z01ABCDEFGHIJ', 'test.sgraph.ai',
                                           Enum__Route53__Record_Type.A)
        assert isinstance(result, Schema__Route53__Change__Result)
        batch  = self.client.client().last_change_batch
        action = batch['Changes'][0]['Action']
        assert action == 'DELETE'

    def test__delete_record__raises_if_record_not_found(self):
        with pytest.raises(ValueError, match='not found'):
            self.client.delete_record('Z01ABCDEFGHIJ', 'nope.sgraph.ai',
                                      Enum__Route53__Record_Type.A)

    # ── P1: get_change / wait_for_change ──────────────────────────────────────

    def test__get_change__returns_typed_result(self):
        result = self.client.get_change('/change/CFAKE123')
        assert isinstance(result, Schema__Route53__Change__Result)
        assert result.status == 'INSYNC'                                              # Default script

    def test__get_change__strips_change_prefix_when_calling_boto3(self):
        self.client.get_change('/change/CFAKE123')                                    # Should not raise — the prefix is stripped before the boto3 call
        assert self.client.client().get_change_calls == 1

    def test__wait_for_change__returns_immediately_when_insync(self):
        result = self.client.wait_for_change('/change/CFAKE123', timeout=10, poll_interval=0)
        assert result.status == 'INSYNC'
        assert self.client.client().get_change_calls == 1                             # One poll, immediate INSYNC

    def test__wait_for_change__polls_until_insync(self):
        self.client.client().get_change_script = ['PENDING', 'PENDING', 'INSYNC']
        result = self.client.wait_for_change('/change/CFAKE123', timeout=10, poll_interval=0)
        assert result.status == 'INSYNC'
        assert self.client.client().get_change_calls == 3

    def test__wait_for_change__returns_pending_on_timeout(self):
        self.client.client().get_change_script = ['PENDING']                          # Sticky PENDING → wait_for_change should bail out
        result = self.client.wait_for_change('/change/CFAKE123', timeout=0, poll_interval=0)
        assert result.status == 'PENDING'

    def test__wait_for_change__invokes_on_poll_callback(self):
        self.client.client().get_change_script = ['PENDING', 'INSYNC']
        ticks = []
        self.client.wait_for_change('/change/CFAKE123', timeout=10, poll_interval=0,
                                     on_poll=lambda r, t: ticks.append(r.status))
        assert ticks == ['PENDING', 'INSYNC']
