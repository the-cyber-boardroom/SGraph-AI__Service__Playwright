# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Podman__Service.create_node (T2.1)
# Hand-rolled stub collaborators — no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                   import TestCase

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base          import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Info                           import Schema__Node__Info
from sg_compute.primitives.enums.Enum__Node__State                             import Enum__Node__State
from sg_compute_specs.podman.schemas.Schema__Podman__Create__Request           import Schema__Podman__Create__Request
from sg_compute_specs.podman.schemas.Schema__Podman__Create__Response          import Schema__Podman__Create__Response
from sg_compute_specs.podman.service.Podman__AMI__Helper                       import Podman__AMI__Helper
from sg_compute_specs.podman.service.Podman__AWS__Client                       import Podman__AWS__Client
from sg_compute_specs.podman.service.Podman__Launch__Helper                    import Podman__Launch__Helper
from sg_compute_specs.podman.service.Podman__SG__Helper                        import Podman__SG__Helper
from sg_compute_specs.podman.service.Podman__Stack__Mapper                     import Podman__Stack__Mapper
from sg_compute_specs.podman.service.Podman__Tags__Builder                     import Podman__Tags__Builder
from sg_compute_specs.podman.service.Podman__User_Data__Builder                import Podman__User_Data__Builder
from sg_compute_specs.podman.service.Random__Stack__Name__Generator            import Random__Stack__Name__Generator
from sg_compute_specs.podman.service.Podman__Service                           import Podman__Service
from sg_compute_specs.podman.service.Caller__IP__Detector                      import Caller__IP__Detector as Podman__IP__Detector
from sg_compute_specs.podman.primitives.Safe_Str__IP__Address                  import Safe_Str__IP__Address


class _FakeSG(Podman__SG__Helper):
    def ensure_security_group(self, region, stack_name, caller_ip,
                               inbound_ports=None, extra_ports=None):
        return 'sg-fake-podman'


class _FakeAMI(Podman__AMI__Helper):
    def latest_al2023_ami_id(self, region):
        return _FAKE_AMI_ID


_FAKE_INSTANCE_ID = 'i-0a1b2c3d4e5f67890'                                      # 17 hex chars; matches ^i-[0-9a-f]{17}$
_FAKE_AMI_ID      = 'ami-0a1b2c3d4e5f67891'                                    # 17 hex chars; matches ^ami-[0-9a-f]{17}$


class _FakeLaunch(Podman__Launch__Helper):
    def run_instance(self, region, ami_id, sg_id, user_data, tags,
                     instance_type='t3.medium', instance_profile_name=''):
        return _FAKE_INSTANCE_ID


class _FakeTags(Podman__Tags__Builder):
    def build(self, stack_name, caller_ip, creator=''):
        return [{'Key': 'StackName', 'Value': str(stack_name)}]


class _FakeAWSClient(Podman__AWS__Client):
    def __init__(self):
        object.__setattr__(self, 'sg'      , _FakeSG()    )
        object.__setattr__(self, 'ami'     , _FakeAMI()   )
        object.__setattr__(self, 'launch'  , _FakeLaunch())
        object.__setattr__(self, 'tags'    , _FakeTags()  )
        object.__setattr__(self, 'instance', None         )


class _FakeIPDetector(Podman__IP__Detector):
    def detect(self):
        return Safe_Str__IP__Address('10.0.0.1')


def _make_service():
    svc = Podman__Service()
    object.__setattr__(svc, 'aws_client'        , _FakeAWSClient()            )
    object.__setattr__(svc, 'user_data_builder'  , Podman__User_Data__Builder())
    object.__setattr__(svc, 'mapper'             , Podman__Stack__Mapper()    )
    object.__setattr__(svc, 'ip_detector'        , _FakeIPDetector()          )
    object.__setattr__(svc, 'name_gen'           , Random__Stack__Name__Generator())
    return svc


class test_Podman__Service__create_node(TestCase):

    def setUp(self):
        self.svc = _make_service()

    def test_create_node__returns_schema_node_info(self):
        req  = Schema__Node__Create__Request__Base(
            spec_id       = 'podman'      ,
            node_name     = 'pd-test-001' ,
            region        = 'eu-west-2'   ,
            instance_type = 't3.medium'   ,
            caller_ip     = '1.2.3.4'     ,
        )
        info = self.svc.create_node(req, api_key_ssm_path='/sg-compute/nodes/pd-test-001/sidecar-api-key')
        assert isinstance(info, Schema__Node__Info)

    def test_create_node__spec_id_is_podman(self):
        req  = Schema__Node__Create__Request__Base(
            spec_id   = 'podman'     ,
            node_name = 'pd-test-002',
            region    = 'eu-west-2'  ,
        )
        info = self.svc.create_node(req, api_key_ssm_path='/test/path')
        assert info.spec_id == 'podman'

    def test_create_node__state_is_booting(self):
        req  = Schema__Node__Create__Request__Base(
            spec_id   = 'podman'     ,
            node_name = 'pd-test-003',
            region    = 'eu-west-2'  ,
        )
        info = self.svc.create_node(req, api_key_ssm_path='/test/path')
        assert info.state == Enum__Node__State.BOOTING

    def test_create_node__instance_id_populated(self):
        req  = Schema__Node__Create__Request__Base(
            spec_id   = 'podman'     ,
            node_name = 'pd-test-004',
            region    = 'eu-west-2'  ,
        )
        info = self.svc.create_node(req, api_key_ssm_path='/test/path')
        assert info.instance_id == _FAKE_INSTANCE_ID

    def test_create_node__ssm_path_stored(self):
        ssm_path = '/sg-compute/nodes/pd-test-005/sidecar-api-key'
        req      = Schema__Node__Create__Request__Base(
            spec_id   = 'podman'     ,
            node_name = 'pd-test-005',
            region    = 'eu-west-2'  ,
        )
        info = self.svc.create_node(req, api_key_ssm_path=ssm_path)
        assert info.host_api_key_ssm_path == ssm_path

    def test_create_node__passes_api_key_ssm_path_to_user_data(self):
        rendered = []
        original_render = Podman__User_Data__Builder.render

        class _CapturingBuilder(Podman__User_Data__Builder):
            def render(self, stack_name, region, max_hours=1, registry='', api_key_ssm_path=''):
                rendered.append({'registry': registry, 'api_key_ssm_path': api_key_ssm_path})
                return original_render(self, stack_name, region, max_hours=max_hours,
                                       registry=registry, api_key_ssm_path=api_key_ssm_path)

        svc = _make_service()
        svc.user_data_builder = _CapturingBuilder()
        req = Schema__Node__Create__Request__Base(
            spec_id   = 'podman'     ,
            node_name = 'pd-test-006',
            region    = 'eu-west-2'  ,
        )
        svc.create_node(req, api_key_ssm_path='/test/ssm/path')
        assert rendered[0]['api_key_ssm_path'] == '/test/ssm/path'

    def test_create_stack__api_key_ssm_path_threaded_through(self):
        req  = Schema__Podman__Create__Request(
            stack_name       = 'pd-stack-x'      ,
            region           = 'eu-west-2'        ,
            caller_ip        = '1.1.1.1'          ,
            from_ami         = _FAKE_AMI_ID        ,
            api_key_ssm_path = '/ssm/test'        ,
            registry         = 'ecr-host'         ,
        )
        resp = self.svc.create_stack(req)
        assert isinstance(resp, Schema__Podman__Create__Response)
        assert resp.stack_info.instance_id == _FAKE_INSTANCE_ID
