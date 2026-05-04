# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.wait_until_ready
# Drives the polling loop using:
#   - fixture_probe_sequence on the in-memory HTTP client (so each tick sees
#     a different probe status)
#   - sleep_fn=lambda _: None so the test does not actually sleep
# Asserts the on_progress callback gets one tick per poll with the right
# probe + message fields, and that the final Info is READY when the probe
# eventually returns READY.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Kibana__Probe__Status    import Enum__Kibana__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Wait__Tick           import Schema__Wait__Tick
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service, PROBE_MESSAGES
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory


REGION = 'eu-west-2'


def build_running_service(probe_sequence):                                          # Factory — one running instance with a scripted probe sequence
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami       = DEFAULT_FIXTURE_AMI  ,
                                           fixture_instances = {}                   ,
                                           fixture_sg_id     = 'sg-0fixture00000000',
                                           terminated_ids    = []                   ,
                                           deleted_sg_ids    = []                   ,
                                           ssm_calls         = []                   )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready   = False          ,
                                            fixture_probe_sequence = list(probe_sequence),
                                            bulk_calls             = []             )
    service = Elastic__Service(aws_client        = aws                                  ,
                               http_client       = http                                 ,
                               ip_detector       = Caller__IP__Detector__In_Memory()    ,
                               user_data_builder = Elastic__User__Data__Builder()       ,
                               data_generator    = Synthetic__Data__Generator(seed=1)   )
    service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
    instance_id = next(iter(aws.fixture_instances))                                  # Backfill a public IP + running state so the probe path is reached
    aws.fixture_instances[instance_id]['PublicIpAddress'] = '203.0.113.10'
    aws.fixture_instances[instance_id]['State']           = {'Name': 'running'}
    return service


class test_wait_until_ready(TestCase):

    def test_ready_on_first_probe__returns_immediately(self):
        service = build_running_service([Enum__Kibana__Probe__Status.READY])
        ticks   = []
        info    = service.wait_until_ready(stack_name   = Safe_Str__Elastic__Stack__Name('only'),
                                           region       = REGION                                ,
                                           timeout      = 60                                    ,
                                           poll_seconds = 1                                     ,
                                           on_progress  = ticks.append                          ,
                                           sleep_fn     = lambda _: None                        )
        assert info.state  == Enum__Elastic__State.READY
        assert len(ticks)  == 1
        assert type(ticks[0]) is Schema__Wait__Tick
        assert ticks[0].probe == Enum__Kibana__Probe__Status.READY
        assert str(ticks[0].message) == str(PROBE_MESSAGES[Enum__Kibana__Probe__Status.READY])

    def test_progress_through_states__unreachable_then_502_then_ready(self):
        service = build_running_service([Enum__Kibana__Probe__Status.UNREACHABLE   ,
                                         Enum__Kibana__Probe__Status.UPSTREAM_DOWN ,
                                         Enum__Kibana__Probe__Status.READY         ])
        ticks   = []
        info    = service.wait_until_ready(stack_name   = Safe_Str__Elastic__Stack__Name('only'),
                                           region       = REGION                                ,
                                           timeout      = 60                                    ,
                                           poll_seconds = 1                                     ,
                                           on_progress  = ticks.append                          ,
                                           sleep_fn     = lambda _: None                        )
        assert info.state     == Enum__Elastic__State.READY
        assert len(ticks)     == 3
        probes = [t.probe for t in ticks]
        assert probes == [Enum__Kibana__Probe__Status.UNREACHABLE   ,
                          Enum__Kibana__Probe__Status.UPSTREAM_DOWN ,
                          Enum__Kibana__Probe__Status.READY         ]
        assert [t.attempt for t in ticks] == [1, 2, 3]
        assert ticks[-1].elapsed_ms >= 0                                            # Monotonic timer runs even with zero sleeps

    def test_upstream_down_message_is_human_friendly(self):                         # The 502 case is the one the user will see most — check the copy
        service = build_running_service([Enum__Kibana__Probe__Status.UPSTREAM_DOWN ,
                                         Enum__Kibana__Probe__Status.READY         ])
        ticks   = []
        service.wait_until_ready(stack_name   = Safe_Str__Elastic__Stack__Name('only'),
                                 region       = REGION                                ,
                                 timeout      = 60                                    ,
                                 poll_seconds = 1                                     ,
                                 on_progress  = ticks.append                          ,
                                 sleep_fn     = lambda _: None                        )
        assert 'nginx is up' in str(ticks[0].message).lower()
        assert 'kibana'      in str(ticks[0].message).lower()


class test_Elastic__HTTP__Client__probe_classification(TestCase):                   # Unit-level coverage for the status-code → probe-enum mapping

    def test_probe__maps_5xx_to_upstream_down(self):
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client import Elastic__HTTP__Client

        class Fake502(Elastic__HTTP__Client):
            def request(self, method, url, *, headers=None, data=None):
                class R: status_code = 502
                return R()
        assert Fake502().kibana_probe('https://x/') == Enum__Kibana__Probe__Status.UPSTREAM_DOWN

    def test_probe__maps_200_to_ready(self):
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client import Elastic__HTTP__Client

        class Fake200(Elastic__HTTP__Client):
            def request(self, method, url, *, headers=None, data=None):
                class R: status_code = 200
                return R()
        assert Fake200().kibana_probe('https://x/') == Enum__Kibana__Probe__Status.READY

    def test_probe__maps_connection_error_to_unreachable(self):
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client import Elastic__HTTP__Client

        class FakeBoom(Elastic__HTTP__Client):
            def request(self, method, url, *, headers=None, data=None):
                raise ConnectionError('refused')
        assert FakeBoom().kibana_probe('https://x/') == Enum__Kibana__Probe__Status.UNREACHABLE

    def test_probe__maps_3xx_4xx_to_booting(self):
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client import Elastic__HTTP__Client

        class Fake404(Elastic__HTTP__Client):
            def request(self, method, url, *, headers=None, data=None):
                class R: status_code = 404
                return R()
        assert Fake404().kibana_probe('https://x/') == Enum__Kibana__Probe__Status.BOOTING
