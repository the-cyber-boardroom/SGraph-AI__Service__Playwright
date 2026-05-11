# ═══════════════════════════════════════════════════════════════════════════════
# tests — PR-4 stack lifecycle events
# Verifies that each enabled plugin service emits the correct event topic and
# payload when create_stack / delete (create for elastic) / delete_stack
# succeeds. Uses fake AWS collaborators — no real AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus

# ── shared fake collaborators ─────────────────────────────────────────────────

class _Fake_SG:
    def ensure_security_group(self, region, stack_name, caller_ip, extra_ports=None, public=False, open_to_all=False):
        return 'sg-fake'

class _Fake_Tags:
    def build(self, *args, **kwargs): return {}

FAKE_INSTANCE_ID = 'i-0123456789abcdef0'                                            # 17 hex chars — satisfies Safe_Str__Instance__Id regex

class _Fake_Launch:
    def run_instance(self, region, ami_id, sg_id, user_data, tags, **kwargs):
        return FAKE_INSTANCE_ID

class _Fake_Instance:
    def __init__(self, terminate_ok=True):
        self.terminate_ok = terminate_ok
    def find_by_stack_name(self, region, stack_name): return {'InstanceId': FAKE_INSTANCE_ID}
    def terminate_instance(self, region, iid):        return self.terminate_ok
    def list_stacks(self, region):                    return {}

class _Fake_AWS_Client:
    def __init__(self, terminate_ok=True):
        self.sg       = _Fake_SG()
        self.tags     = _Fake_Tags()
        self.launch   = _Fake_Launch()
        self.instance = _Fake_Instance(terminate_ok=terminate_ok)

class _Fake_UDB:
    def render(self, *args, **kwargs): return ''

class _Fake_Name_Gen:
    def generate(self): return 'generated'

class _Fake_IP_Detector:
    def detect(self): return '1.2.3.4'


# ── Podman ────────────────────────────────────────────────────────────────────

class test_Podman__Service__events(TestCase):

    def setUp(self):
        event_bus.reset()

    def _service(self, terminate_ok=True):
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Service       import Podman__Service
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Stack__Mapper import Podman__Stack__Mapper
        svc                  = Podman__Service()
        svc.aws_client       = _Fake_AWS_Client(terminate_ok=terminate_ok)
        svc.user_data_builder= _Fake_UDB()
        svc.name_gen         = _Fake_Name_Gen()
        svc.ip_detector      = _Fake_IP_Detector()
        svc.mapper           = Podman__Stack__Mapper()
        return svc

    def test__create_stack__emits_created_event(self):
        from sgraph_ai_service_playwright__cli.podman.schemas.Schema__Podman__Create__Request import Schema__Podman__Create__Request
        created = []
        event_bus.on('podman:stack.created', lambda e: created.append(e))
        self._service().create_stack(Schema__Podman__Create__Request(
            stack_name='podman-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert len(created) == 1
        assert created[0].type_id         == Enum__Stack__Type.PODMAN
        assert str(created[0].stack_name) == 'podman-test'
        assert str(created[0].region)     == 'eu-west-2'
        assert str(created[0].instance_id)== FAKE_INSTANCE_ID

    def test__delete_stack__emits_deleted_event_on_success(self):
        deleted = []
        event_bus.on('podman:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=True).delete_stack('eu-west-2', 'podman-test')
        assert len(deleted) == 1
        assert deleted[0].type_id         == Enum__Stack__Type.PODMAN
        assert str(deleted[0].stack_name) == 'podman-test'

    def test__delete_stack__no_event_when_terminate_fails(self):
        deleted = []
        event_bus.on('podman:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=False).delete_stack('eu-west-2', 'podman-test')
        assert deleted == []


# ── Docker ────────────────────────────────────────────────────────────────────

class test_Docker__Service__events(TestCase):

    def setUp(self):
        event_bus.reset()

    def _service(self, terminate_ok=True):
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Service       import Docker__Service
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Stack__Mapper import Docker__Stack__Mapper
        svc                  = Docker__Service()
        svc.aws_client       = _Fake_AWS_Client(terminate_ok=terminate_ok)
        svc.user_data_builder= _Fake_UDB()
        svc.name_gen         = _Fake_Name_Gen()
        svc.ip_detector      = _Fake_IP_Detector()
        svc.mapper           = Docker__Stack__Mapper()
        return svc

    def test__create_stack__emits_created_event(self):
        from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
        created = []
        event_bus.on('docker:stack.created', lambda e: created.append(e))
        self._service().create_stack(Schema__Docker__Create__Request(
            stack_name='docker-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert len(created) == 1
        assert created[0].type_id         == Enum__Stack__Type.DOCKER
        assert str(created[0].stack_name) == 'docker-test'
        assert str(created[0].instance_id)== FAKE_INSTANCE_ID

    def test__delete_stack__emits_deleted_event_on_success(self):
        deleted = []
        event_bus.on('docker:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=True).delete_stack('eu-west-2', 'docker-test')
        assert len(deleted) == 1
        assert deleted[0].type_id == Enum__Stack__Type.DOCKER

    def test__delete_stack__no_event_when_terminate_fails(self):
        deleted = []
        event_bus.on('docker:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=False).delete_stack('eu-west-2', 'docker-test')
        assert deleted == []


# ── Elastic ───────────────────────────────────────────────────────────────────

class test_Elastic__Service__events(TestCase):

    def setUp(self):
        event_bus.reset()

    def _service(self, terminate_ok=True):
        from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
        from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory
        from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory import Kibana__Saved_Objects__Client__In_Memory
        from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service          import Elastic__Service
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
        from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator
        aws = Elastic__AWS__Client__In_Memory(
            fixture_ami      = DEFAULT_FIXTURE_AMI  ,
            fixture_instances= {}                   ,
            fixture_sg_id    = 'sg-0fixture00000000',
            terminated_ids   = []                   ,
            deleted_sg_ids   = []                   ,
            ssm_calls        = []                   )
        if not terminate_ok:
            aws.terminated_ids = None               # causes terminate_instance to return False
        return Elastic__Service(
            aws_client           = aws                                    ,
            http_client          = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready=True, fixture_probe_sequence=[], bulk_calls=[]),
            saved_objects_client = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[]),
            ip_detector          = Caller__IP__Detector__In_Memory()      ,
            user_data_builder    = Elastic__User__Data__Builder()         ,
            data_generator       = Synthetic__Data__Generator(seed=0)     )

    def test__create__emits_created_event(self):
        from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request import Schema__Elastic__Create__Request
        created = []
        event_bus.on('elastic:stack.created', lambda e: created.append(e))
        self._service().create(Schema__Elastic__Create__Request(region='eu-west-2'))
        assert len(created) == 1
        assert created[0].type_id         == Enum__Stack__Type.ELASTIC
        assert str(created[0].region)     == 'eu-west-2'
        assert str(created[0].instance_id)!= ''

    def test__delete_stack__emits_deleted_event_on_success(self):
        from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
        from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client              import TAG_STACK_NAME_KEY
        svc = self._service()
        iid = 'i-0abc1234567890def'
        svc.aws_client.fixture_instances = {iid: {'InstanceId': iid, 'Tags': [
            {'Key': TAG_STACK_NAME_KEY, 'Value': 'elastic-test'},
            {'Key': 'Purpose'         , 'Value': 'sp-elastic'  }], 'SecurityGroups': [], 'State': {'Name': 'running'}}}
        deleted = []
        event_bus.on('elastic:stack.deleted', lambda e: deleted.append(e))
        svc.delete_stack(Safe_Str__Elastic__Stack__Name('elastic-test'))
        assert len(deleted) == 1
        assert deleted[0].type_id == Enum__Stack__Type.ELASTIC


# ── VNC ───────────────────────────────────────────────────────────────────────

class test_Vnc__Service__events(TestCase):

    def setUp(self):
        event_bus.reset()

    def _service(self, terminate_ok=True):
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service    import Vnc__Service
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper import Vnc__Stack__Mapper

        class _Fake_Interceptor_Resolver:
            def resolve(self, interceptor): return ('', '')

        class _Fake_Compose_Template:
            def render(self): return 'compose: {}'

        svc                      = Vnc__Service()
        svc.aws_client           = _Fake_AWS_Client(terminate_ok=terminate_ok)
        svc.user_data_builder    = _Fake_UDB()
        svc.name_gen             = _Fake_Name_Gen()
        svc.ip_detector          = _Fake_IP_Detector()
        svc.mapper               = Vnc__Stack__Mapper()
        svc.interceptor_resolver = _Fake_Interceptor_Resolver()
        svc.compose_template     = _Fake_Compose_Template()
        return svc

    def test__create_stack__emits_created_event(self):
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        created = []
        event_bus.on('vnc:stack.created', lambda e: created.append(e))
        self._service().create_stack(Schema__Vnc__Stack__Create__Request(
            stack_name='vnc-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert len(created) == 1
        assert created[0].type_id         == Enum__Stack__Type.VNC
        assert str(created[0].stack_name) == 'vnc-test'
        assert str(created[0].instance_id)== FAKE_INSTANCE_ID

    def test__delete_stack__emits_deleted_event_on_success(self):
        deleted = []
        event_bus.on('vnc:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=True).delete_stack('eu-west-2', 'vnc-test')
        assert len(deleted) == 1
        assert deleted[0].type_id == Enum__Stack__Type.VNC

    def test__delete_stack__no_event_when_terminate_fails(self):
        deleted = []
        event_bus.on('vnc:stack.deleted', lambda e: deleted.append(e))
        self._service(terminate_ok=False).delete_stack('eu-west-2', 'vnc-test')
        assert deleted == []
