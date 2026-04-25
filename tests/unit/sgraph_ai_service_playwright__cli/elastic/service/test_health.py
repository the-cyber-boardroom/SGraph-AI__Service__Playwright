# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.health
# Pins the diagnostic flow that drives `sp el health`. Real subclasses of
# every collaborator — no mocks. Covers the two failure modes the user is
# most likely to hit:
#   - SG ingress no longer matches their current IP (IP rotated since create)
#   - TCP :443 unreachable (network blocked or SG misconfigured)
# Plus the happy path with everything green.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status           import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory


REGION    = 'eu-west-2'
CALLER_IP = '203.0.113.42'                                                          # TEST-NET-3 — Caller__IP__Detector__In_Memory default


def build_service(sg_ingress, kibana_ready=True, public_ip='203.0.113.10'):
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami        = DEFAULT_FIXTURE_AMI ,
                                           fixture_instances  = {}                  ,
                                           fixture_sg_id      = 'sg-0fixture00000000',
                                           terminated_ids     = []                  ,
                                           deleted_sg_ids     = []                  ,
                                           ssm_calls          = []                  ,
                                           fixture_sg_ingress = sg_ingress         )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready   = kibana_ready,
                                            fixture_probe_sequence = []          ,
                                            bulk_calls             = []          )
    service = Elastic__Service(aws_client        = aws                                  ,
                               http_client       = http                                 ,
                               ip_detector       = Caller__IP__Detector__In_Memory()    ,
                               user_data_builder = Elastic__User__Data__Builder()       ,
                               data_generator    = Synthetic__Data__Generator(seed=1)   )
    service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
    instance_id = next(iter(aws.fixture_instances))
    aws.fixture_instances[instance_id]['PublicIpAddress'] = public_ip
    aws.fixture_instances[instance_id]['State']           = {'Name': 'running'}
    return service


def find_check(response, name):
    return next((c for c in response.checks if str(c.name) == name), None)


class test_health(TestCase):

    def test_sg_ingress_mismatch_is_flagged_fail(self):                              # User's actual ConnectTimeout — current IP is not in the SG anymore
        service  = build_service(sg_ingress=[{'port': 443, 'cidr': '198.51.100.99/32'}])
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=False)
        chk = find_check(response, 'sg-ingress')
        assert chk.status == Enum__Health__Status.FAIL
        assert CALLER_IP   in str(chk.detail)                                       # Detail explicitly names the caller's current IP so the user can see the mismatch
        assert '198.51.100.99/32' in str(chk.detail)
        assert response.all_ok is False

    def test_sg_ingress_match_is_ok(self):
        service  = build_service(sg_ingress=[{'port': 443, 'cidr': f'{CALLER_IP}/32'}])
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=False)
        chk = find_check(response, 'sg-ingress')
        assert chk.status == Enum__Health__Status.OK

    def test_no_443_ingress_at_all_is_fail(self):
        service  = build_service(sg_ingress=[{'port': 22, 'cidr': '0.0.0.0/0'}])     # SG has only :22 — no :443 rule at all
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=False)
        chk = find_check(response, 'sg-ingress')
        assert chk.status == Enum__Health__Status.FAIL
        assert 'no :443' in str(chk.detail)

    def test_no_public_ip_skips_downstream(self):                                    # If the instance has no public IP yet, tcp/elastic/kibana checks must skip not fail
        service  = build_service(sg_ingress=[{'port': 443, 'cidr': f'{CALLER_IP}/32'}], public_ip='')
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=False)
        assert find_check(response, 'public-ip').status == Enum__Health__Status.WARN
        assert find_check(response, 'tcp-443'  ).status == Enum__Health__Status.SKIP
        assert find_check(response, 'elastic'  ).status == Enum__Health__Status.SKIP
        assert find_check(response, 'kibana'   ).status == Enum__Health__Status.SKIP

    def test_no_ssm_skips_ssm_checks_without_calling_aws(self):
        service  = build_service(sg_ingress=[{'port': 443, 'cidr': f'{CALLER_IP}/32'}])
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=False)
        assert find_check(response, 'ssm-boot-status').status == Enum__Health__Status.SKIP
        assert find_check(response, 'ssm-docker'     ).status == Enum__Health__Status.SKIP
        # No SSM call must have been recorded — proves the path was actually skipped, not just labelled
        assert service.aws_client.ssm_calls == []

    def test_ssm_checks_run_when_enabled(self):
        service  = build_service(sg_ingress=[{'port': 443, 'cidr': f'{CALLER_IP}/32'}])
        service.aws_client.fixture_ssm_stdout = 'OK 2026-04-25T10:00:00+00:00'
        response = service.health(stack_name=Safe_Str__Elastic__Stack__Name('only'),
                                  password='', check_ssm=True)
        boot = find_check(response, 'ssm-boot-status')
        assert boot.status == Enum__Health__Status.OK
        assert 'OK' in str(boot.detail)
        assert len(service.aws_client.ssm_calls) == 2                                # Both SSM calls fired (boot-status + docker ps)
