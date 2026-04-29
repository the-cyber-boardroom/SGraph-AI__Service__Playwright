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
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Probe                import Vnc__HTTP__Probe
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper              import Vnc__Stack__Mapper

        s = Vnc__Service()
        assert s.setup() is s
        assert isinstance(s.aws_client , Vnc__AWS__Client              )
        assert isinstance(s.probe      , Vnc__HTTP__Probe              )
        assert isinstance(s.mapper     , Vnc__Stack__Mapper            )
        assert isinstance(s.ip_detector, Caller__IP__Detector          )
        assert isinstance(s.name_gen   , Random__Stack__Name__Generator)
