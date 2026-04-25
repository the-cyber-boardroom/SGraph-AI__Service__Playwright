# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.list_amis / create_ami_from_stack / delete_ami
# Real subclass-and-override AWS client — no mocks. Pins the AMI list/create/
# delete contract that drives `sp el ami {list,create,delete}`.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory       import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory       import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory      import Elastic__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory import Kibana__Saved_Objects__Client__In_Memory


REGION = 'eu-west-2'


def build_service(amis=None) -> Elastic__Service:
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami       = DEFAULT_FIXTURE_AMI ,
                                           fixture_instances = {}                  ,
                                           fixture_sg_id     = 'sg-0fixture00000000',
                                           terminated_ids    = []                  ,
                                           deleted_sg_ids    = []                  ,
                                           ssm_calls         = []                  ,
                                           fixture_amis      = list(amis or []))
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready=True, fixture_probe_sequence=[], bulk_calls=[])
    saved = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[], dashboard_calls=[], harden_calls=[])
    return Elastic__Service(aws_client           = aws                                 ,
                            http_client          = http                                ,
                            saved_objects_client = saved                               ,
                            ip_detector          = Caller__IP__Detector__In_Memory()   ,
                            user_data_builder    = Elastic__User__Data__Builder()      ,
                            data_generator       = Synthetic__Data__Generator(seed=1)  )


class test_list_amis(TestCase):

    def test_empty_when_no_amis(self):
        service = build_service(amis=[])
        amis    = service.list_amis(region=REGION)
        assert len(amis) == 0

    def test_maps_raw_aws_payload_to_schema(self):
        service = build_service(amis=[
            {'ami_id': 'ami-aaa', 'name': 'sg-elastic-ami-foo-100',
             'description': 'desc', 'creation_date': '2026-04-25T10:00:00.000Z',
             'state': 'available', 'source_stack': 'foo', 'source_id': 'i-1', 'snapshot_ids': ['snap-1']},
            {'ami_id': 'ami-bbb', 'name': 'sg-elastic-ami-bar-200',
             'description': '', 'creation_date': '2026-04-25T11:00:00.000Z',
             'state': 'pending', 'source_stack': 'bar', 'source_id': 'i-2', 'snapshot_ids': []},
        ])
        amis = service.list_amis(region=REGION)
        assert len(amis) == 2
        assert str(amis[0].ami_id)       == 'ami-aaa'
        assert str(amis[0].source_stack) == 'foo'
        assert str(amis[0].state)        == 'available'
        assert str(amis[1].state)        == 'pending'


class test_create_ami_from_stack(TestCase):

    def test_records_call_with_default_ami_name(self):                              # No --name supplied → service synthesises sg-elastic-ami-<stack>-<unix-ts>
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        iid = next(iter(service.aws_client.fixture_instances))
        service.aws_client.fixture_instances[iid]['State'] = {'Name': 'running'}
        result = service.create_ami_from_stack(stack_name=Safe_Str__Elastic__Stack__Name('only'))
        assert result['error']       == ''
        assert result['ami_id'].startswith('ami-fixture')
        assert result['instance_id'] == iid
        assert len(service.aws_client.created_amis) == 1
        captured = service.aws_client.created_amis[0]
        assert captured['stack_name'].startswith('only') or captured['stack_name'] == 'only'
        assert captured['ami_name'].startswith('Ephemeral Kibana')                  # Default name pattern: "Ephemeral Kibana - <stack> - <ts>"
        assert captured['no_reboot'] is True                                        # Default: don't reboot ES while baking

    def test_honours_custom_name_and_reboot_flag(self):
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        iid = next(iter(service.aws_client.fixture_instances))
        service.aws_client.fixture_instances[iid]['State'] = {'Name': 'running'}
        result = service.create_ami_from_stack(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                               ami_name='my-ami', no_reboot=False)
        assert result['error']  == ''
        captured = service.aws_client.created_amis[0]
        assert captured['ami_name']  == 'my-ami'
        assert captured['no_reboot'] is False

    def test_no_such_stack_returns_error(self):
        service = build_service()
        result  = service.create_ami_from_stack(stack_name=Safe_Str__Elastic__Stack__Name('ghost'))
        assert result['ami_id']      == ''
        assert 'no such stack'       in result['error']
        assert service.aws_client.created_amis == []


class test_delete_ami(TestCase):

    def test_deregisters_and_records(self):
        service = build_service()
        result  = service.delete_ami(ami_id='ami-toremove', region=REGION)
        assert result['deregistered']      is True
        assert result['snapshots_deleted'] == 1
        assert service.aws_client.deregistered_amis == [(REGION, 'ami-toremove')]
