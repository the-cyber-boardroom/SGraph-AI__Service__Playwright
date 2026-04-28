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


class test_setup_chain(TestCase):                                                   # OpenSearch__Service().setup() should wire all 5 helpers

    def test__setup_returns_self_and_wires_helpers(self):
        from sgraph_ai_service_playwright__cli.opensearch.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client         import OpenSearch__AWS__Client
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Probe         import OpenSearch__HTTP__Probe
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Stack__Mapper       import OpenSearch__Stack__Mapper
        from sgraph_ai_service_playwright__cli.opensearch.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator

        s = OpenSearch__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client , OpenSearch__AWS__Client       )
        assert isinstance(s.probe      , OpenSearch__HTTP__Probe       )
        assert isinstance(s.mapper     , OpenSearch__Stack__Mapper     )
        assert isinstance(s.ip_detector, Caller__IP__Detector          )
        assert isinstance(s.name_gen   , Random__Stack__Name__Generator)
