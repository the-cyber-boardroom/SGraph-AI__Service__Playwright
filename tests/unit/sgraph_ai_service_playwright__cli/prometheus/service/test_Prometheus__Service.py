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
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Probe         import Prometheus__HTTP__Probe
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Stack__Mapper       import Prometheus__Stack__Mapper
        from sgraph_ai_service_playwright__cli.prometheus.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator

        s = Prometheus__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client , Prometheus__AWS__Client       )
        assert isinstance(s.probe      , Prometheus__HTTP__Probe       )
        assert isinstance(s.mapper     , Prometheus__Stack__Mapper     )
        assert isinstance(s.ip_detector, Caller__IP__Detector          )
        assert isinstance(s.name_gen   , Random__Stack__Name__Generator)
