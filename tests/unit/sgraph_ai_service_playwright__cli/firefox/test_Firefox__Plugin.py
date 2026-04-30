# ═══════════════════════════════════════════════════════════════════════════════
# tests — Firefox plugin
# Covers: manifest shape, catalog entry, registry discovery, service stub
# paths (create/delete/list) via fake AWS collaborators, event bus wiring.
# No real AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                 import Plugin__Registry
from sgraph_ai_service_playwright__cli.firefox.plugin.Plugin__Manifest__Firefox     import Plugin__Manifest__Firefox
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service             import Firefox__Service


FAKE_INSTANCE_ID = 'i-0123456789abcdef0'


# ── fake AWS collaborators ────────────────────────────────────────────────────

class _Fake_SG:
    def ensure_security_group(self, region, stack_name, caller_ip): return 'sg-fake'

class _Fake_AMI:
    def latest_al2023_ami_id(self, region): return 'ami-0a1b2c3d4e5f60000'

class _Fake_Tags:
    def build(self, *args, **kwargs): return []

class _Fake_Launch:
    def run_instance(self, region, ami_id, sg_id, user_data, tags,
                     instance_type='', instance_profile_name=''): return FAKE_INSTANCE_ID

class _Fake_Instance:
    def __init__(self, terminate_ok=True):
        self.terminate_ok = terminate_ok
    def find_by_stack_name(self, region, stack_name): return {'InstanceId': FAKE_INSTANCE_ID, 'Tags': [], 'State': {'Name': 'running'}}
    def terminate_instance(self, region, iid):        return self.terminate_ok
    def list_stacks(self, region):                    return {}

class _Fake_AWS_Client:
    def __init__(self, terminate_ok=True):
        self.sg       = _Fake_SG()
        self.ami      = _Fake_AMI()
        self.tags     = _Fake_Tags()
        self.launch   = _Fake_Launch()
        self.instance = _Fake_Instance(terminate_ok=terminate_ok)

class _Fake_UDB:
    def render(self, *args, **kwargs): return ''

class _Fake_Name_Gen:
    def generate(self): return 'bold-turing'

class _Fake_IP_Detector:
    def detect(self): return '1.2.3.4'


def _service(terminate_ok=True) -> Firefox__Service:
    from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Stack__Mapper import Firefox__Stack__Mapper
    svc                  = Firefox__Service()
    svc.aws_client       = _Fake_AWS_Client(terminate_ok=terminate_ok)
    svc.user_data_builder= _Fake_UDB()
    svc.name_gen         = _Fake_Name_Gen()
    svc.ip_detector      = _Fake_IP_Detector()
    svc.mapper           = Firefox__Stack__Mapper()
    return svc


# ═══════════════════════════════════════════════════════════════════════════════

class test_Firefox__Manifest(TestCase):

    def test__manifest__enabled_true(self):
        assert Plugin__Manifest__Firefox().enabled is True

    def test__manifest__stability_experimental(self):
        from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability import Enum__Plugin__Stability
        assert Plugin__Manifest__Firefox().stability == Enum__Plugin__Stability.EXPERIMENTAL

    def test__manifest__service_class_is_firefox_service(self):
        assert Plugin__Manifest__Firefox().service_class() is Firefox__Service

    def test__manifest__routes_classes_nonempty(self):
        from sgraph_ai_service_playwright__cli.firefox.fast_api.routes.Routes__Firefox__Stack import Routes__Firefox__Stack
        assert Routes__Firefox__Stack in Plugin__Manifest__Firefox().routes_classes()

    def test__catalog_entry__type_id_is_firefox(self):
        assert Plugin__Manifest__Firefox().catalog_entry().type_id == Enum__Stack__Type.FIREFOX

    def test__catalog_entry__available_true(self):
        assert Plugin__Manifest__Firefox().catalog_entry().available is True

    def test__catalog_entry__endpoints_reference_firefox_prefix(self):
        entry = Plugin__Manifest__Firefox().catalog_entry()
        assert '/firefox/' in entry.create_endpoint_path
        assert '/firefox/' in entry.list_endpoint_path


class test_Firefox__Registry(TestCase):

    def setUp(self):
        event_bus.reset()

    def test__registry__discovers_firefox_when_enabled(self):
        loaded = []
        event_bus.on('core:plugin.loaded', lambda e: loaded.append(e))
        registry = Plugin__Registry()
        registry.plugin_folders = ['firefox']
        registry.discover()
        assert 'firefox' in registry.manifests
        assert len(loaded) == 1
        assert loaded[0].name == 'firefox'

    def test__registry__skips_firefox_via_env_override(self):
        import os
        skipped = []
        event_bus.on('core:plugin.skipped', lambda e: skipped.append(e))
        os.environ['PLUGIN__FIREFOX__ENABLED'] = 'false'
        try:
            registry = Plugin__Registry()
            registry.plugin_folders = ['firefox']
            registry.discover()
            assert 'firefox' not in registry.manifests
            assert skipped[0].reason == 'env-override-disabled'
        finally:
            del os.environ['PLUGIN__FIREFOX__ENABLED']


class test_Firefox__Service(TestCase):

    def setUp(self):
        event_bus.reset()

    def test__create_stack__returns_response_with_instance_id(self):
        from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
        svc    = _service()
        result = svc.create_stack(Schema__Firefox__Stack__Create__Request(
            stack_name='firefox-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert str(result.instance_id) == FAKE_INSTANCE_ID
        assert str(result.stack_name)  == 'firefox-test'

    def test__create_stack__emits_created_event(self):
        from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
        created = []
        event_bus.on('firefox:stack.created', lambda e: created.append(e))
        _service().create_stack(Schema__Firefox__Stack__Create__Request(
            stack_name='firefox-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert len(created) == 1
        assert created[0].type_id == Enum__Stack__Type.FIREFOX
        assert str(created[0].stack_name) == 'firefox-test'

    def test__delete_stack__emits_deleted_event_on_success(self):
        deleted = []
        event_bus.on('firefox:stack.deleted', lambda e: deleted.append(e))
        result = _service(terminate_ok=True).delete_stack('eu-west-2', 'firefox-test')
        assert result.deleted is True
        assert len(deleted) == 1
        assert deleted[0].type_id == Enum__Stack__Type.FIREFOX

    def test__delete_stack__no_event_when_terminate_fails(self):
        deleted = []
        event_bus.on('firefox:stack.deleted', lambda e: deleted.append(e))
        result = _service(terminate_ok=False).delete_stack('eu-west-2', 'firefox-test')
        assert result.deleted is False
        assert deleted == []

    def test__list_stacks__returns_empty_list(self):
        result = _service().list_stacks('eu-west-2')
        assert result.total == 0

    def test__create_stack__auto_generates_password(self):
        from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
        result = _service().create_stack(Schema__Firefox__Stack__Create__Request(
            stack_name='firefox-test', region='eu-west-2', caller_ip='1.2.3.4', from_ami='ami-0a1b2c3d4e5f60000'))
        assert str(result.password) != ''

    def test__viewer_url__uses_http_port_5800(self):
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Stack__Mapper import Firefox__Stack__Mapper
        mapper = Firefox__Stack__Mapper()
        info   = mapper.to_info({'InstanceId': FAKE_INSTANCE_ID, 'Tags': [], 'State': {'Name': 'running'},
                                  'PublicIpAddress': '1.2.3.4'}, 'eu-west-2')
        assert str(info.viewer_url) == 'http://1.2.3.4:5800/'
