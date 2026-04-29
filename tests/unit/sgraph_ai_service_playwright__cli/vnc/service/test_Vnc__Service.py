# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Service (read paths)
# Compose the real helpers but inject in-memory fakes for the AWS + HTTP
# boundaries. No mocks anywhere. create_stack lands in step 7f.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import (TAG_ALLOWED_IP_KEY    ,
                                                                                              TAG_INTERCEPTOR_KEY   ,
                                                                                              TAG_STACK_NAME_KEY    )
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import Vnc__Service


def _details(stack_name='vnc-quiet-fermi', state='running', public_ip='5.6.7.8', interceptor='none'):
    return {'InstanceId'     : 'i-0123456789abcdef0'                                       ,
            'ImageId'        : 'ami-0685f8dd865c8e389'                                     ,
            'InstanceType'   : 't3.medium'                                                 ,
            'PublicIpAddress': public_ip                                                    ,
            'State'          : {'Name': state}                                              ,
            'SecurityGroups' : [{'GroupId': 'sg-1234567890abcdef0'}]                        ,
            'Tags'           : [{'Key': 'Name'              , 'Value': f'vnc-{stack_name}'},
                                {'Key': TAG_STACK_NAME_KEY  , 'Value': stack_name         },
                                {'Key': TAG_ALLOWED_IP_KEY  , 'Value': '1.2.3.4'          },
                                {'Key': TAG_INTERCEPTOR_KEY , 'Value': interceptor        }]}


class _Fake_Instance__Helper:
    def __init__(self, world=None, terminate_ok=True):
        self.world        = world or {}
        self.terminate_ok = terminate_ok
        self.terminated   = []
    def list_stacks(self, region):                       return self.world
    def find_by_stack_name(self, region, stack_name):
        for d in self.world.values():
            for tag in d.get('Tags', []):
                if tag.get('Key') == TAG_STACK_NAME_KEY and tag.get('Value') == stack_name:
                    return d
        return None
    def terminate_instance(self, region, iid):
        self.terminated.append(iid)
        return self.terminate_ok


class _Fake_AWS_Client:
    def __init__(self, instance_helper):
        self.instance = instance_helper


class _Fake_Probe:
    def __init__(self, nginx=False, mitmweb=False, flows=None):
        self.nginx   = nginx
        self.mitmweb = mitmweb
        self.flows   = flows or []
    def nginx_ready  (self, base_url, username='', password=''): return self.nginx
    def mitmweb_ready(self, base_url, username='', password=''): return self.mitmweb
    def flows_listing(self, base_url, username='', password=''): return self.flows


def _service(world=None, nginx=False, mitmweb=False, flows=None, terminate_ok=True) -> Vnc__Service:
    from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper import Vnc__Stack__Mapper
    s = Vnc__Service()
    s.aws_client = _Fake_AWS_Client(_Fake_Instance__Helper(world or {}, terminate_ok=terminate_ok))
    s.probe      = _Fake_Probe(nginx=nginx, mitmweb=mitmweb, flows=flows)
    s.mapper     = Vnc__Stack__Mapper()
    return s


class test_list_stacks(TestCase):

    def test__empty_world(self):
        listing = _service().list_stacks('eu-west-2')
        assert list(listing.stacks) == []

    def test__two_stacks_mapped(self):
        world   = {'i-aaa': _details('vnc-aaa'), 'i-bbb': _details('vnc-bbb')}
        listing = _service(world=world).list_stacks('eu-west-2')
        names   = sorted(str(info.stack_name) for info in listing.stacks)
        assert names == ['vnc-aaa', 'vnc-bbb']


class test_get_stack_info(TestCase):

    def test__hit(self):
        info = _service(world={'i-aaa': _details('vnc-aaa')}).get_stack_info('eu-west-2', 'vnc-aaa')
        assert info is not None
        assert str(info.viewer_url)  == 'https://5.6.7.8/'
        assert str(info.mitmweb_url) == 'https://5.6.7.8/mitmweb/'

    def test__miss(self):
        assert _service().get_stack_info('eu-west-2', 'no-such') is None


class test_delete_stack(TestCase):

    def test__hit(self):
        s    = _service(world={'i-aaa': _details('vnc-aaa')})
        resp = s.delete_stack('eu-west-2', 'vnc-aaa')
        assert str(resp.target)                  == 'i-0123456789abcdef0'
        assert [str(iid) for iid in resp.terminated_instance_ids] == ['i-0123456789abcdef0']

    def test__miss_returns_empty(self):
        resp = _service().delete_stack('eu-west-2', 'no-such')
        assert str(resp.target) == ''
        assert list(resp.terminated_instance_ids) == []


class test_health(TestCase):

    def test__no_instance_returns_error(self):
        h = _service().health('eu-west-2', 'no-such')
        assert 'instance not running' in str(h.error)

    def test__no_public_ip_returns_error(self):
        s = _service(world={'i-aaa': _details('vnc-aaa', state='pending', public_ip='')})
        h = s.health('eu-west-2', 'vnc-aaa')
        assert 'public IP' in str(h.error)

    def test__nginx_and_mitmweb_ready_marks_ready_and_counts_flows(self):
        flows = [{'id': 'f1'}, {'id': 'f2'}, {'id': 'f3'}]
        s     = _service(world={'i-aaa': _details('vnc-aaa')}, nginx=True, mitmweb=True, flows=flows)
        h     = s.health('eu-west-2', 'vnc-aaa')
        assert h.state      == Enum__Vnc__Stack__State.READY
        assert h.nginx_ok   is True
        assert h.mitmweb_ok is True
        assert h.flow_count == 3

    def test__nginx_ok_but_mitmweb_unreachable_keeps_running_state_and_sentinel(self):
        s = _service(world={'i-aaa': _details('vnc-aaa')}, nginx=True, mitmweb=False)
        h = s.health('eu-west-2', 'vnc-aaa')
        assert h.state      == Enum__Vnc__Stack__State.RUNNING                       # only flips to READY when both are up
        assert h.nginx_ok   is True
        assert h.mitmweb_ok is False
        assert h.flow_count == -1


class test_flows(TestCase):

    def test__no_instance_returns_empty(self):
        out = _service().flows('eu-west-2', 'no-such')
        assert list(out) == []

    def test__maps_mitmweb_payload_to_summaries(self):
        flows = [{'id': 'aaa', 'request': {'method': 'GET' , 'pretty_url': 'https://example.com/x'},
                  'response': {'status_code': 200}, 'timestamp_created': '2026-04-29T10:00:00Z'},
                 {'id': 'bbb', 'request': {'method': 'POST', 'url': 'https://example.com/y'}}]
        s   = _service(world={'i-aaa': _details('vnc-aaa')}, flows=flows)
        out = list(s.flows('eu-west-2', 'vnc-aaa'))
        assert len(out)               == 2
        assert str(out[0].method)     == 'GET'
        assert str(out[0].url)        == 'https://example.com/x'
        assert out[0].status_code     == 200
        assert str(out[1].method)     == 'POST'
        assert out[1].status_code     == 0                                          # No response yet


class test_setup_chain(TestCase):

    def test__setup_returns_self_and_wires_helpers(self):
        from sgraph_ai_service_playwright__cli.vnc.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.vnc.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                import Vnc__AWS__Client
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Compose__Template          import Vnc__Compose__Template
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Probe                import Vnc__HTTP__Probe
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Interceptor__Resolver      import Vnc__Interceptor__Resolver
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper              import Vnc__Stack__Mapper
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__User_Data__Builder         import Vnc__User_Data__Builder

        s = Vnc__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client          , Vnc__AWS__Client              )
        assert isinstance(s.probe               , Vnc__HTTP__Probe              )
        assert isinstance(s.mapper              , Vnc__Stack__Mapper            )
        assert isinstance(s.ip_detector         , Caller__IP__Detector          )
        assert isinstance(s.name_gen            , Random__Stack__Name__Generator)
        assert isinstance(s.compose_template    , Vnc__Compose__Template        )
        assert isinstance(s.user_data_builder   , Vnc__User_Data__Builder       )
        assert isinstance(s.interceptor_resolver, Vnc__Interceptor__Resolver    )


# ──────────────────────────────── create_stack (Phase B step 7f) ────────────────

class _Fake_SG__Helper:
    def __init__(self): self.calls = []; self.sg_id = 'sg-fake-vnc-1234567'
    def ensure_security_group(self, region, stack_name, caller_ip, public=False):
        self.calls.append((region, str(stack_name), str(caller_ip), bool(public)))
        return self.sg_id


class _Fake_AMI__Helper:
    def __init__(self, ami='ami-0685f8dd865c8e389'): self.ami = ami; self.calls = []
    def latest_al2023_ami_id(self, region):
        self.calls.append(region)
        return self.ami


class _Fake_Tags__Builder:
    def __init__(self): self.calls = []
    def build(self, stack_name, caller_ip, creator='', interceptor=None):
        self.calls.append({'stack_name' : str(stack_name) ,
                            'caller_ip'  : str(caller_ip)  ,
                            'creator'    : str(creator)    ,
                            'interceptor': interceptor     })
        return [{'Key': 'Name'        , 'Value': f'vnc-{stack_name}'},
                {'Key': 'sg:purpose'  , 'Value': 'vnc'              }]


class _Fake_Launch__Helper:
    def __init__(self, instance_id='i-0123456789abcdef0'):
        self.instance_id = instance_id
        self.calls       = []
    def run_instance(self, region, ami_id, security_group_id, user_data, tags, instance_type='t3.large', instance_profile_name=None):
        self.calls.append({'region': region, 'ami_id': ami_id, 'sg_id': security_group_id,
                           'user_data': user_data, 'tags': tags, 'instance_type': instance_type,
                           'instance_profile_name': instance_profile_name})
        return self.instance_id


class _Fake_AWS_Client__Full:
    def __init__(self):
        self.sg       = _Fake_SG__Helper()
        self.ami      = _Fake_AMI__Helper()
        self.tags     = _Fake_Tags__Builder()
        self.launch   = _Fake_Launch__Helper()
        self.instance = _Fake_Instance__Helper()


class _Fake_Compose__Template:
    def __init__(self): self.calls = []
    def render(self, chromium_image=None, mitmproxy_image=None):
        self.calls.append('render')
        return 'services:\n  chromium:\n    image: lscr.io/linuxserver/chromium:latest\n'


class _Fake_User_Data__Builder:
    def __init__(self): self.calls = []
    def render(self, *, stack_name, region, compose_yaml, interceptor_source,
                       operator_password, interceptor_kind='none'):
        self.calls.append({'stack_name'        : stack_name        ,
                            'region'            : region            ,
                            'compose_yaml_len'  : len(compose_yaml) ,
                            'interceptor_source': interceptor_source,
                            'operator_password' : operator_password ,
                            'interceptor_kind'  : interceptor_kind  })
        return f'#!/usr/bin/env bash\necho stack={stack_name} kind={interceptor_kind}\n'


class _Fake_Interceptor__Resolver:
    def __init__(self, source='# noop\n', label=''):
        self.source = source; self.label = label; self.calls = []
    def resolve(self, choice=None):
        self.calls.append(choice)
        return self.source, self.label


class _Fake_IP_Detector_static:
    def __init__(self, ip='1.2.3.4'): self.ip = ip
    def detect(self): return self.ip


class _Fake_Name_Gen_static:
    def __init__(self, name='quiet-fermi'): self.name = name
    def generate(self): return self.name


def _service_for_create(resolver=None) -> Vnc__Service:
    s = Vnc__Service()
    s.aws_client           = _Fake_AWS_Client__Full()
    s.ip_detector          = _Fake_IP_Detector_static()
    s.name_gen             = _Fake_Name_Gen_static()
    s.compose_template     = _Fake_Compose__Template()
    s.user_data_builder    = _Fake_User_Data__Builder()
    s.interceptor_resolver = resolver or _Fake_Interceptor__Resolver()
    return s


class test_create_stack(TestCase):

    def test__empty_request_resolves_all_defaults(self):
        from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s    = _service_for_create()
        resp = s.create_stack(Schema__Vnc__Stack__Create__Request())

        assert str(resp.stack_name)        == 'vnc-quiet-fermi'                      # 'vnc-' + name_gen output
        assert str(resp.aws_name_tag)      == 'vnc-quiet-fermi'                      # VNC_NAMING does not double the prefix
        assert str(resp.instance_id)       == 'i-0123456789abcdef0'
        assert str(resp.region)            == 'eu-west-2'
        assert str(resp.ami_id)            == 'ami-0685f8dd865c8e389'                 # latest_al2023
        assert str(resp.caller_ip)         == '1.2.3.4'                               # ip_detector
        assert str(resp.security_group_id) == 'sg-fake-vnc-1234567'
        assert str(resp.instance_type)     == 't3.large'                              # DEFAULT_INSTANCE_TYPE
        assert str(resp.operator_password)                                             # Generated, non-empty
        assert resp.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NONE       # Default-off per N5
        assert str(resp.interceptor_name)  == ''                                       # NONE → empty label

    def test__name_interceptor_flows_into_response(self):
        from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        choice   = Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name='header_logger')
        resolver = _Fake_Interceptor__Resolver(source='# baked example\n', label='header_logger')
        s        = _service_for_create(resolver=resolver)
        resp     = s.create_stack(Schema__Vnc__Stack__Create__Request(interceptor=choice))

        assert resp.interceptor_kind       == Enum__Vnc__Interceptor__Kind.NAME
        assert str(resp.interceptor_name)  == 'header_logger'
        assert resolver.calls[0] is not None                                          # resolver got the choice
        assert s.user_data_builder.calls[0]['interceptor_source'] == '# baked example\n'
        assert s.user_data_builder.calls[0]['interceptor_kind']   == 'name'

    def test__operator_password_flows_into_user_data_only(self):                     # Defensive — secret never goes near tags or compose
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s   = _service_for_create()
        s.create_stack(Schema__Vnc__Stack__Create__Request(operator_password='SECRETPWD-1234567890'))

        assert s.user_data_builder.calls[0]['operator_password'] == 'SECRETPWD-1234567890'
        tags_call = s.aws_client.tags.calls[0]
        assert tags_call['caller_ip'] == '1.2.3.4'
        assert 'SECRETPWD' not in str(tags_call)

    def test__sg_ingress_uses_resolved_caller_ip(self):
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Vnc__Stack__Create__Request())
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[2] == '1.2.3.4'
        assert sg_call[3] is False                                                   # Default → caller /32 only

    def test__public_ingress_flows_to_sg_helper(self):                                # --open / public_ingress=True opens 443 to 0.0.0.0/0
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Vnc__Stack__Create__Request(public_ingress=True))
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[3] is True

    def test__request_overrides_take_priority(self):
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s    = _service_for_create()
        req  = Schema__Vnc__Stack__Create__Request(stack_name='vnc-prod', region='us-east-1',
                                                     instance_type='t3.xlarge',
                                                     from_ami='ami-1111222233334444a',
                                                     caller_ip='9.9.9.9',
                                                     operator_password='YYYYZZZZ-1234567890abc')
        resp = s.create_stack(req, creator='tester@example.com')
        assert str(resp.stack_name)        == 'vnc-prod'
        assert str(resp.region)            == 'us-east-1'
        assert str(resp.instance_type)     == 't3.xlarge'
        assert str(resp.ami_id)            == 'ami-1111222233334444a'
        assert s.aws_client.ami.calls      == []
        assert str(resp.caller_ip)         == '9.9.9.9'
        assert str(resp.operator_password) == 'YYYYZZZZ-1234567890abc'

    def test__launch_call_carries_correct_user_data_and_tags(self):
        from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Vnc__Stack__Create__Request())
        launch_call = s.aws_client.launch.calls[0]
        assert launch_call['ami_id']                == 'ami-0685f8dd865c8e389'
        assert launch_call['sg_id']                 == 'sg-fake-vnc-1234567'
        assert launch_call['instance_type']         == 't3.large'
        assert launch_call['instance_profile_name'] == 'playwright-ec2'                  # Required so SSM agent can register — `sp vnc connect` fails with TargetNotConnected when missing
        assert 'echo stack=vnc-quiet-fermi'         in launch_call['user_data']
        assert any(t['Key'] == 'Name' for t in launch_call['tags'])
