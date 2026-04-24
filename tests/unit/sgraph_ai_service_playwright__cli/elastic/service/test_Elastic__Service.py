# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service
# Drives the full create / list / info / delete / seed flow against the
# in-memory subclasses of all collaborators. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info  import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Response import Schema__Elastic__Create__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Delete__Response import Schema__Elastic__Delete__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List        import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Request    import Schema__Elastic__Seed__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Response   import Schema__Elastic__Seed__Response
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory


REGION = 'eu-west-2'


def build_service(kibana_ready: bool = True) -> Elastic__Service:
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami       = DEFAULT_FIXTURE_AMI ,
                                           fixture_instances = {}                  ,
                                           fixture_sg_id     = 'sg-0fixture00000000',
                                           terminated_ids    = []                  ,
                                           deleted_sg_ids    = []                  )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready = kibana_ready ,
                                            bulk_calls           = []           )
    return Elastic__Service(aws_client        = aws                                  ,
                            http_client       = http                                 ,
                            ip_detector       = Caller__IP__Detector__In_Memory()    ,
                            user_data_builder = Elastic__User__Data__Builder()       ,
                            data_generator    = Synthetic__Data__Generator(seed=99)  )


class test_Elastic__Service(TestCase):

    def test__init__(self):
        with Elastic__Service() as _:                                               # Construct without injection — collaborators auto-init
            assert type(_.aws_client       ).__name__ == 'Elastic__AWS__Client'
            assert type(_.http_client      ).__name__ == 'Elastic__HTTP__Client'
            assert type(_.ip_detector      ).__name__ == 'Caller__IP__Detector'
            assert type(_.user_data_builder).__name__ == 'Elastic__User__Data__Builder'
            assert type(_.data_generator   ).__name__ == 'Synthetic__Data__Generator'

    def test_create__autogenerates_name_and_ip(self):                               # No NAME / no caller_ip provided → service fills both
        service  = build_service()
        request  = Schema__Elastic__Create__Request(region=REGION)
        response = service.create(request)

        assert type(response)                  is Schema__Elastic__Create__Response
        assert str(response.stack_name)        .startswith('elastic-')              # adjective-scientist
        assert str(response.aws_name_tag)      == f'elastic-{str(response.stack_name)}'
        assert str(response.region)            == REGION
        assert str(response.ami_id)            == DEFAULT_FIXTURE_AMI
        assert str(response.instance_type)     == 't3.medium'
        assert str(response.security_group_id) == 'sg-0fixture00000000'
        assert str(response.caller_ip)         == '203.0.113.42'
        assert str(response.elastic_password)  != ''                                # Generated, returned once
        assert response.state                  == Enum__Elastic__State.PENDING

    def test_create__honours_user_supplied_name(self):
        service  = build_service()
        request  = Schema__Elastic__Create__Request(stack_name='my-stack', region=REGION)
        response = service.create(request)
        assert str(response.stack_name)   == 'my-stack'
        assert str(response.aws_name_tag) == 'elastic-my-stack'                     # Always prefixed in EC2 console

    def test_create__sg_locked_to_caller_ip(self):                                  # Service must pass caller IP into ensure_security_group
        service = build_service()
        service.create(Schema__Elastic__Create__Request(region=REGION))
        assert service.aws_client.last_sg_caller_ip == '203.0.113.42'

    def test_create__user_data_contains_password_and_stack_name(self):
        service  = build_service()
        response = service.create(Schema__Elastic__Create__Request(stack_name='ck-1', region=REGION))
        captured = service.aws_client.last_launch_user_data
        assert f'ELASTIC_PASSWORD={str(response.elastic_password)}' in captured
        assert 'ck-1' in captured

    def test_list_stacks__empty(self):
        service  = build_service()
        response = service.list_stacks(region=REGION)
        assert type(response)        is Schema__Elastic__List
        assert type(response.stacks) is List__Schema__Elastic__Info
        assert len(response.stacks)  == 0

    def test_list_and_get_after_create(self):
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='alpha', region=REGION))
        service.create(Schema__Elastic__Create__Request(stack_name='beta' , region=REGION))

        listing = service.list_stacks(region=REGION)
        assert len(listing.stacks) == 2

        info_alpha = service.get_stack_info(stack_name=Safe_Str__Elastic__Stack__Name('alpha'), region=REGION)
        assert type(info_alpha)       is Schema__Elastic__Info
        assert str(info_alpha.stack_name) == 'alpha'

    def test_get_stack_info__missing_returns_unknown_state(self):
        service = build_service()
        info    = service.get_stack_info(stack_name=Safe_Str__Elastic__Stack__Name('nope'), region=REGION)
        assert type(info)   is Schema__Elastic__Info
        assert info.state   == Enum__Elastic__State.UNKNOWN
        assert str(info.instance_id) == ''

    def test_delete__terminates_and_records(self):
        service  = build_service()
        response = service.create(Schema__Elastic__Create__Request(stack_name='xy', region=REGION))
        result   = service.delete_stack(stack_name=Safe_Str__Elastic__Stack__Name('xy'), region=REGION)

        assert type(result)                         is Schema__Elastic__Delete__Response
        assert type(result.terminated_instance_ids) is List__Instance__Id
        assert len(result.terminated_instance_ids)  == 1
        assert str(result.terminated_instance_ids[0]) == str(response.instance_id)
        assert result.security_group_deleted        is True

    def test_delete__missing_returns_empty_response(self):
        service = build_service()
        result  = service.delete_stack(stack_name=Safe_Str__Elastic__Stack__Name('missing'), region=REGION)
        assert len(result.terminated_instance_ids) == 0

    def test_seed__no_public_ip_returns_zeros(self):                                # Fresh stack: PublicIpAddress='' → seed early-returns
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='ss', region=REGION))
        response = service.seed_stack(Schema__Elastic__Seed__Request(stack_name=Safe_Str__Elastic__Stack__Name('ss'),
                                                                     document_count=10))
        assert type(response)                  is Schema__Elastic__Seed__Response
        assert response.documents_posted       == 0
        assert response.documents_failed       == 0

    def test_seed__posts_in_batches(self):                                          # Once we backfill a public IP, seed batches and totals work
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='ss', region=REGION))
        instance_id = next(iter(service.aws_client.fixture_instances))
        service.aws_client.fixture_instances[instance_id]['PublicIpAddress'] = '198.51.100.10'
        service.aws_client.fixture_instances[instance_id]['State']           = {'Name': 'running'}

        response = service.seed_stack(Schema__Elastic__Seed__Request(
            stack_name      = Safe_Str__Elastic__Stack__Name('ss'),
            document_count  = 250                                ,
            batch_size      = 100                                ,
            elastic_password= 'pw1234567890ABCDEF'                ))

        assert response.documents_posted == 250
        assert response.documents_failed == 0
        assert response.batches          == 3                                       # 100 + 100 + 50
        assert response.duration_ms      > 0
        assert len(service.http_client.bulk_calls) == 3
        for base_url, index, count in service.http_client.bulk_calls:
            assert base_url == 'https://198.51.100.10/'
            assert index    == 'sg-synthetic'
            assert count > 0
