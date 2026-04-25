# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.wipe_seed
# Verifies that a wipe deletes the ES index AND the matching Kibana data view,
# captures both calls, and is idempotent (succeeds when the data view doesn't
# exist). Real subclasses, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory       import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory       import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory      import Elastic__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory import Kibana__Saved_Objects__Client__In_Memory


REGION = 'eu-west-2'


def build_service(view_existed: bool = True) -> Elastic__Service:
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami       = DEFAULT_FIXTURE_AMI ,
                                           fixture_instances = {}                  ,
                                           fixture_sg_id     = 'sg-0fixture00000000',
                                           terminated_ids    = []                  ,
                                           deleted_sg_ids    = []                  ,
                                           ssm_calls         = []                  )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready   = True ,
                                            fixture_probe_sequence = []   ,
                                            bulk_calls             = []   ,
                                            delete_index_calls     = []   )
    saved = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[],
                                                      fixture_view_existed_for_delete=view_existed)
    service = Elastic__Service(aws_client           = aws                                  ,
                               http_client          = http                                 ,
                               saved_objects_client = saved                                ,
                               ip_detector          = Caller__IP__Detector__In_Memory()    ,
                               user_data_builder    = Elastic__User__Data__Builder()       ,
                               data_generator       = Synthetic__Data__Generator(seed=1)   )
    service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
    iid = next(iter(aws.fixture_instances))
    aws.fixture_instances[iid]['PublicIpAddress'] = '203.0.113.10'
    aws.fixture_instances[iid]['State']           = {'Name': 'running'}
    return service


class test_wipe_seed(TestCase):

    def test_deletes_both_index_and_data_view(self):
        service = build_service(view_existed=True)
        result  = service.wipe_seed(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                     index='sg-synthetic', password='pw')
        assert result['index_deleted']      is True
        assert result['data_view_deleted']  is True
        assert result['index_error']        == ''
        assert result['data_view_error']    == ''
        # Both clients recorded the call
        assert service.http_client.delete_index_calls          == [('https://203.0.113.10/', 'sg-synthetic')]
        assert service.saved_objects_client.delete_calls        == [('https://203.0.113.10/', 'sg-synthetic')]

    def test_idempotent_when_data_view_absent(self):
        service = build_service(view_existed=False)
        result  = service.wipe_seed(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                     index='sg-synthetic', password='pw')
        assert result['index_deleted']     is True
        assert result['data_view_deleted'] is False                                  # Idempotent: not found is not an error
        assert result['data_view_error']   == ''
