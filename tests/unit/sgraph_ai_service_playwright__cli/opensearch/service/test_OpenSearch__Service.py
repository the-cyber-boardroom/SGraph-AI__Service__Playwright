# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__Service (read paths)
# Compose the real helpers but inject in-memory fakes for the AWS + HTTP
# boundaries. No mocks anywhere — everything is a real subclass.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client   import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Service       import OpenSearch__Service


def _details(stack_name='os-quiet-fermi', state='running', public_ip='5.6.7.8'):
    return {'InstanceId'     : 'i-0123456789abcdef0'                                       ,
            'ImageId'        : 'ami-0685f8dd865c8e389'                                     ,
            'InstanceType'   : 'm6i.large'                                                 ,
            'PublicIpAddress': public_ip                                                    ,
            'State'          : {'Name': state}                                              ,
            'SecurityGroups' : [{'GroupId': 'sg-1234567890abcdef0'}]                        ,
            'Tags'           : [{'Key': 'Name'              , 'Value': f'opensearch-{stack_name}'},
                                {'Key': TAG_STACK_NAME_KEY  , 'Value': stack_name              },
                                {'Key': TAG_ALLOWED_IP_KEY  , 'Value': '1.2.3.4'               }]}


class _Fake_Instance__Helper:                                                       # Substitutes OpenSearch__Instance__Helper inside aws_client
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


class _Fake_Probe:                                                                  # Substitutes OpenSearch__HTTP__Probe
    def __init__(self, cluster=None, dashboards_ok=False):
        self.cluster        = cluster or {}
        self.dashboards_ok  = dashboards_ok
    def cluster_health(self, base_url, username='', password=''):  return self.cluster
    def dashboards_ready(self, base_url, username='', password=''): return self.dashboards_ok


def _service(world=None, cluster=None, dashboards_ok=False, terminate_ok=True) -> OpenSearch__Service:
    from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Stack__Mapper import OpenSearch__Stack__Mapper
    s = OpenSearch__Service()
    s.aws_client = _Fake_AWS_Client(_Fake_Instance__Helper(world or {}, terminate_ok=terminate_ok))
    s.probe      = _Fake_Probe(cluster=cluster, dashboards_ok=dashboards_ok)
    s.mapper     = OpenSearch__Stack__Mapper()
    return s


class test_list_stacks(TestCase):

    def test__empty_world(self):
        listing = _service().list_stacks('eu-west-2')
        assert str(listing.region)  == 'eu-west-2'
        assert list(listing.stacks) == []

    def test__two_stacks_mapped(self):
        world   = {'i-aaa': _details('os-aaa'), 'i-bbb': _details('os-bbb')}
        listing = _service(world=world).list_stacks('eu-west-2')
        names   = sorted(str(info.stack_name) for info in listing.stacks)
        assert names == ['os-aaa', 'os-bbb']


class test_get_stack_info(TestCase):

    def test__hit(self):
        info = _service(world={'i-aaa': _details('os-aaa')}).get_stack_info('eu-west-2', 'os-aaa')
        assert info is not None
        assert str(info.stack_name) == 'os-aaa'

    def test__miss(self):
        assert _service().get_stack_info('eu-west-2', 'no-such') is None


class test_delete_stack(TestCase):

    def test__hit_returns_terminated_ids(self):
        s     = _service(world={'i-aaa': _details('os-aaa')})
        resp  = s.delete_stack('eu-west-2', 'os-aaa')
        assert str(resp.target)                  == 'i-0123456789abcdef0'
        assert str(resp.stack_name)              == 'os-aaa'
        assert [str(iid) for iid in resp.terminated_instance_ids] == ['i-0123456789abcdef0']

    def test__miss_returns_empty_response(self):
        resp = _service().delete_stack('eu-west-2', 'no-such')
        assert str(resp.target)                  == ''
        assert list(resp.terminated_instance_ids) == []

    def test__terminate_failure_yields_empty_terminated_list(self):
        s     = _service(world={'i-aaa': _details('os-aaa')}, terminate_ok=False)
        resp  = s.delete_stack('eu-west-2', 'os-aaa')
        assert list(resp.terminated_instance_ids) == []                              # Termination didn't succeed


class test_health(TestCase):

    def test__no_instance_returns_error(self):
        h = _service().health('eu-west-2', 'no-such')
        assert h.state == Enum__OS__Stack__State.UNKNOWN
        assert 'instance not running' in str(h.error)

    def test__no_public_ip_returns_error(self):
        s = _service(world={'i-aaa': _details('os-aaa', state='pending', public_ip='')})
        h = s.health('eu-west-2', 'os-aaa')
        assert 'public IP'                         in str(h.error)

    def test__cluster_green_and_dashboards_ok_marks_ready(self):
        cluster = {'status': 'green', 'number_of_nodes': 1, 'active_shards': 5}
        s       = _service(world={'i-aaa': _details('os-aaa')}, cluster=cluster, dashboards_ok=True)
        h       = s.health('eu-west-2', 'os-aaa')
        assert h.state                  == Enum__OS__Stack__State.READY
        assert str(h.cluster_status)    == 'green'
        assert h.node_count             == 1
        assert h.active_shards          == 5
        assert h.dashboards_ok          is True
        assert h.os_endpoint_ok         is True

    def test__cluster_red_keeps_running_state(self):                                # State only flips to READY when both probes succeed
        cluster = {'status': 'red', 'number_of_nodes': 0, 'active_shards': 0}
        s       = _service(world={'i-aaa': _details('os-aaa')}, cluster=cluster, dashboards_ok=False)
        h       = s.health('eu-west-2', 'os-aaa')
        assert h.state                  == Enum__OS__Stack__State.RUNNING
        assert str(h.cluster_status)    == 'red'
        assert h.dashboards_ok          is False


class test_setup_chain(TestCase):                                                   # OpenSearch__Service().setup() should wire all 7 helpers

    def test__setup_returns_self_and_wires_helpers(self):
        from sgraph_ai_service_playwright__cli.opensearch.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client         import OpenSearch__AWS__Client
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Compose__Template   import OpenSearch__Compose__Template
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Probe         import OpenSearch__HTTP__Probe
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Stack__Mapper       import OpenSearch__Stack__Mapper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__User_Data__Builder  import OpenSearch__User_Data__Builder
        from sgraph_ai_service_playwright__cli.opensearch.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator

        s = OpenSearch__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client       , OpenSearch__AWS__Client       )
        assert isinstance(s.probe            , OpenSearch__HTTP__Probe       )
        assert isinstance(s.mapper           , OpenSearch__Stack__Mapper     )
        assert isinstance(s.ip_detector      , Caller__IP__Detector          )
        assert isinstance(s.name_gen         , Random__Stack__Name__Generator)
        assert isinstance(s.compose_template , OpenSearch__Compose__Template )
        assert isinstance(s.user_data_builder, OpenSearch__User_Data__Builder)


# ──────────────────────────────── create_stack (Phase B step 5f.4b) ───────────

class _Fake_SG__Helper:
    def __init__(self): self.calls = []; self.sg_id = 'sg-fake-os-1234567'
    def ensure_security_group(self, region, stack_name, caller_ip):
        self.calls.append((region, str(stack_name), str(caller_ip)))
        return self.sg_id


class _Fake_AMI__Helper:
    def __init__(self, ami='ami-0685f8dd865c8e389'): self.ami = ami; self.calls = []
    def latest_al2023_ami_id(self, region):
        self.calls.append(region)
        return self.ami


class _Fake_Tags__Builder:
    def __init__(self): self.calls = []
    def build(self, stack_name, caller_ip, creator=''):
        self.calls.append((str(stack_name), str(caller_ip), str(creator)))
        return [{'Key': 'Name'        , 'Value': f'opensearch-{stack_name}'},
                {'Key': 'sg:purpose'  , 'Value': 'opensearch'              },
                {'Key': 'sg:stack-name', 'Value': stack_name               }]


class _Fake_Launch__Helper:
    def __init__(self, instance_id='i-0123456789abcdef0'):
        self.instance_id = instance_id
        self.calls       = []
    def run_instance(self, region, ami_id, security_group_id, user_data, tags, instance_type='t3.large', instance_profile_name=None):
        self.calls.append({'region': region, 'ami_id': ami_id, 'sg_id': security_group_id,
                           'user_data': user_data, 'tags': tags, 'instance_type': instance_type})
        return self.instance_id


class _Fake_AWS_Client__Full:                                                       # Composes the per-concern fakes for create_stack
    def __init__(self):
        self.sg       = _Fake_SG__Helper()
        self.ami      = _Fake_AMI__Helper()
        self.tags     = _Fake_Tags__Builder()
        self.launch   = _Fake_Launch__Helper()
        self.instance = _Fake_Instance__Helper()                                    # For list/get/delete cohabitation


class _Fake_Compose__Template:
    def __init__(self): self.calls = []
    def render(self, admin_password, heap_size='2g', os_image=None, dashboards_image=None):
        self.calls.append({'admin_password': admin_password, 'heap_size': heap_size})
        return f'services:\n  opensearch:\n    env: PASSWORD={admin_password}\n'


class _Fake_User_Data__Builder:
    def __init__(self): self.calls = []
    def render(self, stack_name, region, compose_yaml):
        self.calls.append({'stack_name': stack_name, 'region': region, 'compose_yaml_len': len(compose_yaml)})
        return f'#!/usr/bin/env bash\necho stack={stack_name} region={region}\n# compose-len={len(compose_yaml)}\n'


class _Fake_IP_Detector_static:
    def __init__(self, ip='1.2.3.4'): self.ip = ip
    def detect(self): return self.ip


class _Fake_Name_Gen_static:
    def __init__(self, name='quiet-fermi'): self.name = name
    def generate(self): return self.name


def _service_for_create() -> OpenSearch__Service:
    s = OpenSearch__Service()
    s.aws_client        = _Fake_AWS_Client__Full()
    s.ip_detector       = _Fake_IP_Detector_static()
    s.name_gen          = _Fake_Name_Gen_static()
    s.compose_template  = _Fake_Compose__Template()
    s.user_data_builder = _Fake_User_Data__Builder()
    return s


class test_create_stack(TestCase):

    def test__empty_request_resolves_all_defaults(self):
        from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
        s     = _service_for_create()
        resp  = s.create_stack(Schema__OS__Stack__Create__Request())

        assert str(resp.stack_name)        == 'os-quiet-fermi'                       # 'os-' + name_gen output
        assert str(resp.aws_name_tag)      == 'opensearch-os-quiet-fermi'            # OS_NAMING prepends 'opensearch-'
        assert str(resp.instance_id)       == 'i-0123456789abcdef0'
        assert str(resp.region)            == 'eu-west-2'                             # DEFAULT_REGION
        assert str(resp.ami_id)            == 'ami-0685f8dd865c8e389'                 # latest_al2023
        assert str(resp.caller_ip)         == '1.2.3.4'                               # ip_detector
        assert str(resp.security_group_id) == 'sg-fake-os-1234567'
        assert str(resp.admin_password)                                                # Generated, non-empty (~32 chars)
        assert resp.state                  is __import__('sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State',
                                                          fromlist=['Enum__OS__Stack__State']).Enum__OS__Stack__State.PENDING

    def test__request_overrides_take_priority(self):
        from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
        s    = _service_for_create()
        req  = Schema__OS__Stack__Create__Request(stack_name='os-prod'                    ,
                                                   region='us-east-1'                      ,
                                                   instance_type='m6i.large'               ,
                                                   from_ami='ami-1111222233334444a'         ,
                                                   caller_ip='9.9.9.9'                     ,
                                                   admin_password='YYYYZZZZ-1234567890abc')
        resp = s.create_stack(req, creator='tester@example.com')

        assert str(resp.stack_name)        == 'os-prod'                              # No 'os-' prefixing — name was provided
        assert str(resp.aws_name_tag)      == 'opensearch-os-prod'
        assert str(resp.region)            == 'us-east-1'
        assert str(resp.instance_type)     == 'm6i.large'
        assert str(resp.ami_id)            == 'ami-1111222233334444a'                 # ami helper NOT called
        assert s.aws_client.ami.calls      == []                                      # Defensive
        assert str(resp.caller_ip)         == '9.9.9.9'                               # ip_detector NOT called
        assert str(resp.admin_password)    == 'YYYYZZZZ-1234567890abc'                # Generator NOT called

    def test__compose_password_flows_into_user_data_via_compose(self):                # Secret only flows once; user-data does NOT see admin_password directly
        from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
        s    = _service_for_create()
        req  = Schema__OS__Stack__Create__Request(admin_password='SECRETPWD-1234567890')
        s.create_stack(req)

        assert s.compose_template.calls[0]['admin_password'] == 'SECRETPWD-1234567890'
        ud_call = s.user_data_builder.calls[0]
        assert 'admin_password' not in ud_call                                        # Builder signature does not take it
        assert ud_call['compose_yaml_len'] > 0                                        # Compose was rendered + handed in

    def test__sg_ingress_uses_resolved_caller_ip(self):                               # Defensive — auth boundary
        from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__OS__Stack__Create__Request())                          # Empty req → ip_detector kicks in
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[2] == '1.2.3.4'                                                # caller_ip resolved before SG ingress

    def test__launch_call_carries_correct_user_data_and_tags(self):
        from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__OS__Stack__Create__Request())
        launch_call = s.aws_client.launch.calls[0]
        assert launch_call['ami_id']    == 'ami-0685f8dd865c8e389'
        assert launch_call['sg_id']     == 'sg-fake-os-1234567'
        assert 'compose-len='           in launch_call['user_data']                   # Confirms user-data was rendered (fake includes a marker)
        assert any(t['Key'] == 'Name' for t in launch_call['tags'])
