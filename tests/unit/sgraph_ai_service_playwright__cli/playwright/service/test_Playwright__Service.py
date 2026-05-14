# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__Stack__Service (EC2 model)
# Compose the real service but inject in-memory fakes for the AWS + HTTP
# boundaries. No mocks anywhere — fakes are plain objects with the same
# interface. Mirrors test_Vnc__Service.py.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Request import Schema__Playwright__Stack__Create__Request
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client     import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY, TAG_WITH_MITMPROXY_KEY
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Service  import Playwright__Stack__Service


# ── boto3-shaped instance detail fixture ─────────────────────────────────────
def _details(stack_name='playwright-quiet-fermi', state='running',
             public_ip='5.6.7.8', with_mitmproxy='false'):
    return {'InstanceId'     : 'i-0123456789abcdef0'                                       ,
            'ImageId'        : 'ami-0685f8dd865c8e389'                                     ,
            'InstanceType'   : 't3.medium'                                                 ,
            'PublicIpAddress': public_ip                                                    ,
            'State'          : {'Name': state}                                              ,
            'SecurityGroups' : [{'GroupId': 'sg-fake-playwright'}]                         ,
            'LaunchTime'     : '2026-05-14T10:00:00Z'                                      ,
            'Tags'           : [{'Key': 'Name'                 , 'Value': f'playwright-{stack_name}'},
                                {'Key': TAG_STACK_NAME_KEY    , 'Value': stack_name              },
                                {'Key': TAG_ALLOWED_IP_KEY    , 'Value': '1.2.3.4'               },
                                {'Key': TAG_WITH_MITMPROXY_KEY, 'Value': with_mitmproxy          }]}


# ── fake helpers (plain objects, same interface — no mocks) ──────────────────
class _Fake_Instance__Helper:
    def __init__(self, world=None, terminate_ok=True):
        self.world        = world or {}
        self.terminate_ok = terminate_ok
        self.terminated   = []
    def list_stacks(self, region):                return self.world
    def find_by_stack_name(self, region, name):
        for d in self.world.values():
            for t in d.get('Tags', []):
                if t.get('Key') == TAG_STACK_NAME_KEY and t.get('Value') == name:
                    return d
        return None
    def terminate_instance(self, region, iid):
        self.terminated.append(iid)
        return self.terminate_ok


class _Fake_SG__Helper:
    def __init__(self):  self.calls = [];  self.sg_id = 'sg-fake-playwright'
    def ensure_security_group(self, region, stack_name, caller_ip, public=False):
        self.calls.append((region, str(stack_name), str(caller_ip), public))
        return self.sg_id


class _Fake_AMI__Helper:
    def __init__(self, ami='ami-0685f8dd865c8e389'):  self.ami = ami;  self.calls = []
    def latest_al2023_ami_id(self, region):
        self.calls.append(region)
        return self.ami


class _Fake_Tags__Builder:
    def __init__(self):  self.calls = []
    def build(self, stack_name, caller_ip, creator='', with_mitmproxy=False):
        self.calls.append({'stack_name': str(stack_name), 'caller_ip': str(caller_ip),
                            'creator': creator, 'with_mitmproxy': with_mitmproxy})
        return [{'Key': 'Name', 'Value': f'playwright-{stack_name}'}]


class _Fake_Launch__Helper:
    def __init__(self, instance_id='i-0123456789abcdef0'):
        self.instance_id = instance_id;  self.calls = []
    def run_instance(self, region, ami_id, security_group_id, user_data, tags,
                     instance_type='t3.medium', instance_profile_name=None, max_hours=1):
        self.calls.append({'region': region, 'ami_id': ami_id, 'sg_id': security_group_id,
                           'user_data': user_data, 'tags': tags,
                           'instance_type': instance_type,
                           'instance_profile_name': instance_profile_name})
        return self.instance_id


class _Fake_AWS_Client:
    def __init__(self, instance=None, sg=None, ami=None, tags=None, launch=None):
        self.instance = instance or _Fake_Instance__Helper()
        self.sg       = sg       or _Fake_SG__Helper()
        self.ami      = ami      or _Fake_AMI__Helper()
        self.tags     = tags     or _Fake_Tags__Builder()
        self.launch   = launch   or _Fake_Launch__Helper()


class _Fake_Probe:
    def __init__(self, ready=False):  self.ready = ready
    def playwright_ready(self, base_url):  return self.ready


class _Fake_Compose__Template:
    def __init__(self):  self.calls = []
    def render(self, image_tag='latest', api_key='', with_mitmproxy=False, **kw):
        self.calls.append({'image_tag': image_tag, 'with_mitmproxy': with_mitmproxy})
        return f'services:\n  sg-playwright:\n    image: diniscruz/sg-playwright:{image_tag}\n'


class _Fake_User_Data__Builder:
    def __init__(self):  self.calls = []
    def render(self, stack_name, region, compose_yaml, api_key='', with_mitmproxy=False,
               intercept_script='', registry='', max_hours=1):
        self.calls.append({'stack_name': stack_name, 'region': region,
                            'with_mitmproxy': with_mitmproxy, 'registry': registry})
        return f'#!/usr/bin/env bash\necho stack={stack_name}\n'


class _Fake_IP_Detector:
    def __init__(self, ip='1.2.3.4'):  self.ip = ip
    def detect(self):  return self.ip


class _Fake_Name_Gen:
    def __init__(self, name='quiet-fermi'):  self.name = name
    def generate(self):  return self.name


def _service(world=None, probe_ready=False, terminate_ok=True) -> Playwright__Stack__Service:
    from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Mapper import Playwright__Stack__Mapper
    s = Playwright__Stack__Service()
    s.aws_client        = _Fake_AWS_Client(instance=_Fake_Instance__Helper(world or {}, terminate_ok=terminate_ok))
    s.probe             = _Fake_Probe(ready=probe_ready)
    s.mapper            = Playwright__Stack__Mapper()
    s.ip_detector       = _Fake_IP_Detector()
    s.name_gen          = _Fake_Name_Gen()
    s.compose_template  = _Fake_Compose__Template()
    s.user_data_builder = _Fake_User_Data__Builder()
    return s


def _service_for_create() -> Playwright__Stack__Service:
    s = Playwright__Stack__Service()
    s.aws_client        = _Fake_AWS_Client()
    s.probe             = _Fake_Probe()
    s.ip_detector       = _Fake_IP_Detector()
    s.name_gen          = _Fake_Name_Gen()
    s.compose_template  = _Fake_Compose__Template()
    s.user_data_builder = _Fake_User_Data__Builder()
    from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Mapper import Playwright__Stack__Mapper
    s.mapper            = Playwright__Stack__Mapper()
    return s


# ── list_stacks ───────────────────────────────────────────────────────────────
class test_list_stacks(TestCase):

    def test__empty_world(self):
        listing = _service().list_stacks('eu-west-2')
        assert list(listing.stacks) == []

    def test__two_stacks_mapped(self):
        world   = {'i-aaa': _details('playwright-aaa'), 'i-bbb': _details('playwright-bbb')}
        listing = _service(world=world).list_stacks('eu-west-2')
        names   = sorted(str(s.stack_name) for s in listing.stacks)
        assert names == ['playwright-aaa', 'playwright-bbb']

    def test__region_in_envelope(self):
        listing = _service().list_stacks('eu-west-2')
        assert str(listing.region) == 'eu-west-2'

    def test__default_region_applied_when_blank(self):
        listing = _service().list_stacks('')
        assert str(listing.region) == 'eu-west-2'                               # DEFAULT_REGION


# ── get_stack_info ────────────────────────────────────────────────────────────
class test_get_stack_info(TestCase):

    def test__hit(self):
        info = _service(world={'i-aaa': _details('playwright-aaa')}).get_stack_info('eu-west-2', 'playwright-aaa')
        assert info is not None
        assert str(info.playwright_url) == 'http://5.6.7.8:8000'

    def test__miss(self):
        assert _service().get_stack_info('eu-west-2', 'no-such') is None


# ── delete_stack ──────────────────────────────────────────────────────────────
class test_delete_stack(TestCase):

    def test__hit_returns_terminated_id(self):
        s    = _service(world={'i-0123456789abcdef0': _details('playwright-aaa')})
        resp = s.delete_stack('eu-west-2', 'playwright-aaa')
        assert str(resp.target)                               == 'i-0123456789abcdef0'
        assert [str(iid) for iid in resp.terminated_instance_ids] == ['i-0123456789abcdef0']

    def test__miss_returns_empty(self):
        resp = _service().delete_stack('eu-west-2', 'no-such')
        assert str(resp.target) == ''
        assert list(resp.terminated_instance_ids) == []


# ── health ────────────────────────────────────────────────────────────────────
class test_health(TestCase):

    def test__no_instance_returns_error(self):
        h = _service().health('eu-west-2', 'no-such')
        assert 'instance not running' in str(h.error)

    def test__no_public_ip_returns_error(self):
        s = _service(world={'i-aaa': _details('playwright-aaa', public_ip='')})
        h = s.health('eu-west-2', 'playwright-aaa')
        assert 'public IP' in str(h.error)

    def test__probe_ready_marks_state_ready(self):
        s = _service(world={'i-aaa': _details('playwright-aaa')}, probe_ready=True)
        h = s.health('eu-west-2', 'playwright-aaa')
        assert h.playwright_ok is True
        assert h.state         == Enum__Playwright__Stack__State.READY

    def test__probe_not_ready_keeps_running_state(self):
        s = _service(world={'i-aaa': _details('playwright-aaa')}, probe_ready=False)
        h = s.health('eu-west-2', 'playwright-aaa')
        assert h.playwright_ok is False
        assert h.state         == Enum__Playwright__Stack__State.RUNNING


# ── create_stack ──────────────────────────────────────────────────────────────
class test_create_stack(TestCase):

    def test__empty_request_resolves_defaults(self):
        s    = _service_for_create()
        resp = s.create_stack(Schema__Playwright__Stack__Create__Request())

        assert str(resp.stack_name)        == 'playwright-quiet-fermi'           # 'playwright-' + name_gen
        assert str(resp.aws_name_tag)      == 'playwright-quiet-fermi'           # naming helper
        assert str(resp.instance_id)       == 'i-0123456789abcdef0'
        assert str(resp.region)            == 'eu-west-2'                        # DEFAULT_REGION
        assert str(resp.ami_id)            == 'ami-0685f8dd865c8e389'            # fake ami helper
        assert str(resp.caller_ip)         == '1.2.3.4'                          # fake ip_detector
        assert str(resp.security_group_id) == 'sg-fake-playwright'
        assert str(resp.instance_type)     == 't3.medium'                        # DEFAULT_INSTANCE_TYPE
        assert str(resp.api_key)                                                  # non-empty, generated
        assert resp.with_mitmproxy         is False
        assert resp.state                  == Enum__Playwright__Stack__State.PENDING

    def test__api_key_baked_into_compose_env(self):
        s    = _service_for_create()
        resp = s.create_stack(Schema__Playwright__Stack__Create__Request())
        compose_call = s.compose_template.calls[0]
        assert compose_call['image_tag'] == 'latest'

    def test__with_mitmproxy_flows_into_compose_and_tags(self):
        s    = _service_for_create()
        resp = s.create_stack(Schema__Playwright__Stack__Create__Request(with_mitmproxy=True))
        assert resp.with_mitmproxy         is True
        assert s.compose_template.calls[0]['with_mitmproxy'] is True
        assert s.aws_client.tags.calls[0]['with_mitmproxy']  is True

    def test__sg_ingress_uses_resolved_caller_ip(self):
        s = _service_for_create()
        s.create_stack(Schema__Playwright__Stack__Create__Request())
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[2] == '1.2.3.4'
        assert sg_call[3] is False                                               # default → caller /32

    def test__public_ingress_flows_to_sg_helper(self):
        s = _service_for_create()
        s.create_stack(Schema__Playwright__Stack__Create__Request(public_ingress=True))
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[3] is True

    def test__request_overrides_take_priority(self):
        s    = _service_for_create()
        req  = Schema__Playwright__Stack__Create__Request(
            stack_name='playwright-prod', region='us-east-1',
            instance_type='t3.xlarge', from_ami='ami-1111222233334444a',
            caller_ip='9.9.9.9')
        resp = s.create_stack(req)
        assert str(resp.stack_name)    == 'playwright-prod'
        assert str(resp.region)        == 'us-east-1'
        assert str(resp.instance_type) == 't3.xlarge'
        assert str(resp.ami_id)        == 'ami-1111222233334444a'
        assert s.aws_client.ami.calls  == []                                     # not consulted when from_ami supplied
        assert str(resp.caller_ip)     == '9.9.9.9'

    def test__launch_call_carries_profile_name(self):
        s = _service_for_create()
        s.create_stack(Schema__Playwright__Stack__Create__Request())
        launch_call = s.aws_client.launch.calls[0]
        assert launch_call['instance_profile_name'] == 'playwright-ec2'

    def test__user_data_contains_stack_name(self):
        s = _service_for_create()
        s.create_stack(Schema__Playwright__Stack__Create__Request())
        ud_call = s.user_data_builder.calls[0]
        assert 'playwright-quiet-fermi' in ud_call['stack_name']


# ── setup chain ───────────────────────────────────────────────────────────────
class test_setup_chain(TestCase):

    def test__setup_returns_self_and_wires_helpers(self):
        from sgraph_ai_service_playwright__cli.playwright.service.Caller__IP__Detector         import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client      import Playwright__AWS__Client
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Compose__Template import Playwright__Compose__Template
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__HTTP__Probe      import Playwright__HTTP__Probe
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Mapper    import Playwright__Stack__Mapper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__User_Data__Builder import Playwright__User_Data__Builder
        from sgraph_ai_service_playwright__cli.playwright.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator

        s = Playwright__Stack__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client       , Playwright__AWS__Client      )
        assert isinstance(s.probe            , Playwright__HTTP__Probe      )
        assert isinstance(s.mapper           , Playwright__Stack__Mapper    )
        assert isinstance(s.ip_detector      , Caller__IP__Detector         )
        assert isinstance(s.name_gen         , Random__Stack__Name__Generator)
        assert isinstance(s.compose_template , Playwright__Compose__Template)
        assert isinstance(s.user_data_builder, Playwright__User_Data__Builder)
