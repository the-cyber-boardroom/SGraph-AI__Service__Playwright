# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__Service (read paths)
# Compose the real helpers but inject in-memory fakes for the AWS + HTTP
# boundaries. No mocks anywhere — everything is a real subclass.
# create_stack lands in step 6f.4b; not tested here.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Service       import Prometheus__Service


def _details(stack_name='prom-quiet-fermi', state='running', public_ip='5.6.7.8'):
    return {'InstanceId'     : 'i-0123456789abcdef0'                                       ,
            'ImageId'        : 'ami-0685f8dd865c8e389'                                     ,
            'InstanceType'   : 't3.medium'                                                 ,
            'PublicIpAddress': public_ip                                                    ,
            'State'          : {'Name': state}                                              ,
            'SecurityGroups' : [{'GroupId': 'sg-1234567890abcdef0'}]                        ,
            'Tags'           : [{'Key': 'Name'              , 'Value': f'prometheus-{stack_name}'},
                                {'Key': TAG_STACK_NAME_KEY  , 'Value': stack_name              },
                                {'Key': TAG_ALLOWED_IP_KEY  , 'Value': '1.2.3.4'               }]}


class _Fake_Instance__Helper:                                                       # Substitutes Prometheus__Instance__Helper inside aws_client
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


class _Fake_Probe:                                                                  # Substitutes Prometheus__HTTP__Probe
    def __init__(self, ready=False, targets=None):
        self.ready   = ready
        self.targets = targets or {}
    def prometheus_ready(self, base_url, username='', password=''): return self.ready
    def targets_status(self, base_url, username='', password=''):  return self.targets
    def query(self, base_url, query_str, username='', password=''): return {}


def _service(world=None, ready=False, targets=None, terminate_ok=True) -> Prometheus__Service:
    from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Stack__Mapper import Prometheus__Stack__Mapper
    s = Prometheus__Service()
    s.aws_client = _Fake_AWS_Client(_Fake_Instance__Helper(world or {}, terminate_ok=terminate_ok))
    s.probe      = _Fake_Probe(ready=ready, targets=targets)
    s.mapper     = Prometheus__Stack__Mapper()
    return s


class test_list_stacks(TestCase):

    def test__empty_world(self):
        listing = _service().list_stacks('eu-west-2')
        assert str(listing.region)  == 'eu-west-2'
        assert list(listing.stacks) == []

    def test__two_stacks_mapped(self):
        world   = {'i-aaa': _details('prom-aaa'), 'i-bbb': _details('prom-bbb')}
        listing = _service(world=world).list_stacks('eu-west-2')
        names   = sorted(str(info.stack_name) for info in listing.stacks)
        assert names == ['prom-aaa', 'prom-bbb']


class test_get_stack_info(TestCase):

    def test__hit(self):
        info = _service(world={'i-aaa': _details('prom-aaa')}).get_stack_info('eu-west-2', 'prom-aaa')
        assert info is not None
        assert str(info.stack_name)     == 'prom-aaa'
        assert str(info.prometheus_url) == 'http://5.6.7.8:9090/'

    def test__miss(self):
        assert _service().get_stack_info('eu-west-2', 'no-such') is None


class test_delete_stack(TestCase):

    def test__hit_returns_terminated_ids(self):
        s     = _service(world={'i-aaa': _details('prom-aaa')})
        resp  = s.delete_stack('eu-west-2', 'prom-aaa')
        assert str(resp.target)                  == 'i-0123456789abcdef0'
        assert str(resp.stack_name)              == 'prom-aaa'
        assert [str(iid) for iid in resp.terminated_instance_ids] == ['i-0123456789abcdef0']

    def test__miss_returns_empty_response(self):
        resp = _service().delete_stack('eu-west-2', 'no-such')
        assert str(resp.target)                  == ''
        assert list(resp.terminated_instance_ids) == []

    def test__terminate_failure_yields_empty_terminated_list(self):
        s     = _service(world={'i-aaa': _details('prom-aaa')}, terminate_ok=False)
        resp  = s.delete_stack('eu-west-2', 'prom-aaa')
        assert list(resp.terminated_instance_ids) == []                              # Termination didn't succeed


class test_health(TestCase):

    def test__no_instance_returns_error(self):
        h = _service().health('eu-west-2', 'no-such')
        assert h.state == Enum__Prom__Stack__State.UNKNOWN
        assert 'instance not running' in str(h.error)

    def test__no_public_ip_returns_error(self):
        s = _service(world={'i-aaa': _details('prom-aaa', state='pending', public_ip='')})
        h = s.health('eu-west-2', 'prom-aaa')
        assert 'public IP' in str(h.error)

    def test__ready_with_targets_marks_ready_and_counts(self):
        targets = {'data': {'activeTargets': [{'health': 'up'  },
                                              {'health': 'up'  },
                                              {'health': 'down'},
                                              {'health': 'unknown'}]}}
        s = _service(world={'i-aaa': _details('prom-aaa')}, ready=True, targets=targets)
        h = s.health('eu-west-2', 'prom-aaa')
        assert h.state         == Enum__Prom__Stack__State.READY
        assert h.prometheus_ok is True
        assert h.targets_total == 4
        assert h.targets_up    == 2

    def test__not_ready_keeps_running_state(self):                                  # State only flips to READY when /-/healthy returns 200
        s = _service(world={'i-aaa': _details('prom-aaa')}, ready=False)
        h = s.health('eu-west-2', 'prom-aaa')
        assert h.state         == Enum__Prom__Stack__State.RUNNING
        assert h.prometheus_ok is False
        assert h.targets_total == -1                                                # No targets body → sentinels
        assert h.targets_up    == -1

    def test__ready_but_targets_unreachable_uses_sentinels(self):
        s = _service(world={'i-aaa': _details('prom-aaa')}, ready=True, targets={})
        h = s.health('eu-west-2', 'prom-aaa')
        assert h.state         == Enum__Prom__Stack__State.READY
        assert h.prometheus_ok is True
        assert h.targets_total == -1                                                # Empty targets dict ⇒ sentinels (vs. 0 valid count)
        assert h.targets_up    == -1


class test_setup_chain(TestCase):

    def test__setup_returns_self_and_wires_helpers(self):
        from sgraph_ai_service_playwright__cli.prometheus.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client         import Prometheus__AWS__Client
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Compose__Template   import Prometheus__Compose__Template
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Config__Generator   import Prometheus__Config__Generator
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Probe         import Prometheus__HTTP__Probe
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Stack__Mapper       import Prometheus__Stack__Mapper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__User_Data__Builder  import Prometheus__User_Data__Builder
        from sgraph_ai_service_playwright__cli.prometheus.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator

        s = Prometheus__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client       , Prometheus__AWS__Client       )
        assert isinstance(s.probe            , Prometheus__HTTP__Probe       )
        assert isinstance(s.mapper           , Prometheus__Stack__Mapper     )
        assert isinstance(s.ip_detector      , Caller__IP__Detector          )
        assert isinstance(s.name_gen         , Random__Stack__Name__Generator)
        assert isinstance(s.compose_template , Prometheus__Compose__Template )
        assert isinstance(s.config_generator , Prometheus__Config__Generator )
        assert isinstance(s.user_data_builder, Prometheus__User_Data__Builder)


# ──────────────────────────────── create_stack (Phase B step 6f.4b) ────────────

class _Fake_SG__Helper:
    def __init__(self): self.calls = []; self.sg_id = 'sg-fake-prom-1234567'
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
        return [{'Key': 'Name'        , 'Value': f'prometheus-{stack_name}'},
                {'Key': 'sg:purpose'  , 'Value': 'prometheus'              },
                {'Key': 'sg:stack-name', 'Value': stack_name               }]


class _Fake_Launch__Helper:
    def __init__(self, instance_id='i-0123456789abcdef0'):
        self.instance_id = instance_id
        self.calls       = []
    def run_instance(self, region, ami_id, security_group_id, user_data, tags, instance_type='t3.medium', instance_profile_name=None):
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
    def render(self, retention='24h', prom_image=None, cadvisor_image=None, node_exporter_image=None):
        self.calls.append({'retention': retention})
        return 'services:\n  prometheus:\n    image: prom/prometheus:latest\n'


class _Fake_Config__Generator:
    def __init__(self): self.calls = []
    def render(self, targets=None):
        self.calls.append({'target_count': len(targets or [])})
        return 'global:\n  scrape_interval: 15s\nscrape_configs: []\n'


class _Fake_User_Data__Builder:
    def __init__(self): self.calls = []
    def render(self, stack_name, region, compose_yaml, prom_config_yaml):
        self.calls.append({'stack_name': stack_name, 'region': region,
                           'compose_yaml_len': len(compose_yaml),
                           'prom_config_yaml_len': len(prom_config_yaml)})
        return f'#!/usr/bin/env bash\necho stack={stack_name} region={region}\n# compose-len={len(compose_yaml)} cfg-len={len(prom_config_yaml)}\n'


class _Fake_IP_Detector_static:
    def __init__(self, ip='1.2.3.4'): self.ip = ip
    def detect(self): return self.ip


class _Fake_Name_Gen_static:
    def __init__(self, name='quiet-fermi'): self.name = name
    def generate(self): return self.name


def _service_for_create() -> Prometheus__Service:
    s = Prometheus__Service()
    s.aws_client        = _Fake_AWS_Client__Full()
    s.ip_detector       = _Fake_IP_Detector_static()
    s.name_gen          = _Fake_Name_Gen_static()
    s.compose_template  = _Fake_Compose__Template()
    s.config_generator  = _Fake_Config__Generator()
    s.user_data_builder = _Fake_User_Data__Builder()
    return s


class test_create_stack(TestCase):

    def test__empty_request_resolves_all_defaults(self):
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
        s    = _service_for_create()
        resp = s.create_stack(Schema__Prom__Stack__Create__Request())

        assert str(resp.stack_name)        == 'prom-quiet-fermi'                     # 'prom-' + name_gen output
        assert str(resp.aws_name_tag)      == 'prometheus-prom-quiet-fermi'          # PROM_NAMING prepends 'prometheus-'
        assert str(resp.instance_id)       == 'i-0123456789abcdef0'
        assert str(resp.region)            == 'eu-west-2'                             # DEFAULT_REGION
        assert str(resp.ami_id)            == 'ami-0685f8dd865c8e389'                 # latest_al2023
        assert str(resp.caller_ip)         == '1.2.3.4'                               # ip_detector
        assert str(resp.security_group_id) == 'sg-fake-prom-1234567'
        assert str(resp.instance_type)     == 't3.medium'                             # DEFAULT_INSTANCE_TYPE
        assert resp.targets_count          == 0                                       # No baked targets
        assert resp.state                  == Enum__Prom__Stack__State.PENDING

    def test__request_overrides_take_priority(self):
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
        s    = _service_for_create()
        req  = Schema__Prom__Stack__Create__Request(stack_name='prom-prod'                 ,
                                                     region='us-east-1'                     ,
                                                     instance_type='t3.large'               ,
                                                     from_ami='ami-1111222233334444a'        ,
                                                     caller_ip='9.9.9.9'                    )
        resp = s.create_stack(req, creator='tester@example.com')

        assert str(resp.stack_name)        == 'prom-prod'                            # No 'prom-' prefixing — name was provided
        assert str(resp.aws_name_tag)      == 'prometheus-prom-prod'
        assert str(resp.region)            == 'us-east-1'
        assert str(resp.instance_type)     == 't3.large'
        assert str(resp.ami_id)            == 'ami-1111222233334444a'                # ami helper NOT called
        assert s.aws_client.ami.calls      == []
        assert str(resp.caller_ip)         == '9.9.9.9'                               # ip_detector NOT called

    def test__scrape_targets_flow_into_config_generator(self):
        from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target
        from sgraph_ai_service_playwright__cli.prometheus.collections.List__Str             import List__Str
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request

        hosts = List__Str(); hosts.append('1.2.3.4:8000')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='playwright', targets=hosts))
        targets.append(Schema__Prom__Scrape__Target(job_name='other'     , targets=hosts))

        s    = _service_for_create()
        req  = Schema__Prom__Stack__Create__Request(scrape_targets=targets)
        resp = s.create_stack(req)

        assert s.config_generator.calls[0]['target_count'] == 2
        assert resp.targets_count                          == 2

    def test__sg_ingress_uses_resolved_caller_ip(self):
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Prom__Stack__Create__Request())
        sg_call = s.aws_client.sg.calls[0]
        assert sg_call[2] == '1.2.3.4'                                                # caller_ip resolved before SG ingress

    def test__launch_call_carries_correct_user_data_and_tags(self):
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Prom__Stack__Create__Request())
        launch_call = s.aws_client.launch.calls[0]
        assert launch_call['ami_id']                == 'ami-0685f8dd865c8e389'
        assert launch_call['sg_id']                 == 'sg-fake-prom-1234567'
        assert launch_call['instance_type']         == 't3.medium'
        assert launch_call['instance_profile_name'] == 'playwright-ec2'                # Required for SSM agent registration
        assert 'compose-len='                       in launch_call['user_data']         # Confirms user-data was rendered (fake includes a marker)
        assert 'cfg-len='                           in launch_call['user_data']         # Confirms prom_config was passed in
        assert any(t['Key'] == 'Name' for t in launch_call['tags'])

    def test__user_data_takes_both_compose_and_prom_config(self):                    # Builder signature includes prom_config_yaml
        from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
        s = _service_for_create()
        s.create_stack(Schema__Prom__Stack__Create__Request())
        ud_call = s.user_data_builder.calls[0]
        assert ud_call['compose_yaml_len']      > 0
        assert ud_call['prom_config_yaml_len']  > 0
