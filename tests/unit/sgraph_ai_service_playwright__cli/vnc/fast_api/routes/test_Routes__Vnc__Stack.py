# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Routes__Vnc__Stack
# Real subclass overrides Vnc__Service methods to return scripted Type_Safe
# responses. No mocks. FastAPI TestClient drives the endpoints.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional
from unittest                                                                       import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack       import Routes__Vnc__Stack
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request  import Schema__Vnc__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Response import Schema__Vnc__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Delete__Response import Schema__Vnc__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List         import Schema__Vnc__Stack__List
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import Vnc__Service


STACK_NAME  = 'vnc-quiet-fermi'
INSTANCE_ID = 'i-0123456789abcdef0'


def _info():
    return Schema__Vnc__Stack__Info(stack_name        = STACK_NAME              ,
                                      aws_name_tag      = STACK_NAME              ,
                                      instance_id       = INSTANCE_ID             ,
                                      region            = 'eu-west-2'             ,
                                      public_ip         = '5.6.7.8'               ,
                                      viewer_url        = 'https://5.6.7.8/'      ,
                                      mitmweb_url       = 'https://5.6.7.8/mitmweb/',
                                      state             = Enum__Vnc__Stack__State.RUNNING)


def _create_response(stack_name: str = STACK_NAME):
    return Schema__Vnc__Stack__Create__Response(stack_name        = stack_name                  ,
                                                  aws_name_tag      = stack_name                  ,
                                                  instance_id       = INSTANCE_ID                  ,
                                                  region            = 'eu-west-2'                  ,
                                                  operator_password = 'AAAA-BBBB-1234-cdef'        ,
                                                  interceptor_kind  = Enum__Vnc__Interceptor__Kind.NONE,
                                                  state             = Enum__Vnc__Stack__State.PENDING)


class _Fake_Service(Vnc__Service):
    def __init__(self, hit: bool = True, terminate: bool = True):
        super().__init__()
        self.hit              = hit
        self.terminate        = terminate
        self.last_create_req  : Optional[Schema__Vnc__Stack__Create__Request] = None
        self.last_health_args : Optional[tuple]                               = None

    def list_stacks(self, region: str) -> Schema__Vnc__Stack__List:
        stacks = List__Schema__Vnc__Stack__Info()
        if self.hit:
            stacks.append(_info())
        return Schema__Vnc__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Vnc__Stack__Info]:
        return _info() if self.hit else None

    def create_stack(self, request, creator: str = '') -> Schema__Vnc__Stack__Create__Response:
        self.last_create_req = request
        return _create_response(str(request.stack_name) or STACK_NAME)

    def delete_stack(self, region: str, stack_name: str) -> Schema__Vnc__Stack__Delete__Response:
        if not self.hit:
            return Schema__Vnc__Stack__Delete__Response()
        terminated = List__Instance__Id()
        if self.terminate:
            terminated.append(INSTANCE_ID)
        return Schema__Vnc__Stack__Delete__Response(target=INSTANCE_ID, stack_name=stack_name, terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str, username: str = '', password: str = '') -> Schema__Vnc__Health:
        self.last_health_args = (region, stack_name, username, password)
        return Schema__Vnc__Health(stack_name=stack_name, state=Enum__Vnc__Stack__State.READY,
                                     nginx_ok=True, mitmweb_ok=True, flow_count=2)


def _client(service: _Fake_Service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vnc__Stack, service=service)
    return app.client()


class test_list_and_info(TestCase):

    def test_list__non_empty(self):
        c    = _client(_Fake_Service(hit=True))
        resp = c.get('/vnc/stacks')
        assert resp.status_code == 200
        body = resp.json()
        assert body['region']                       == 'eu-west-2'
        assert len(body['stacks'])                  == 1
        assert body['stacks'][0]['stack_name']      == STACK_NAME

    def test_list__empty(self):
        c = _client(_Fake_Service(hit=False))
        assert c.get('/vnc/stacks').json()['stacks'] == []

    def test_info__hit(self):
        c    = _client(_Fake_Service(hit=True))
        resp = c.get(f'/vnc/stack/{STACK_NAME}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['viewer_url']  == 'https://5.6.7.8/'
        assert body['mitmweb_url'] == 'https://5.6.7.8/mitmweb/'

    def test_info__miss_returns_404(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.get('/vnc/stack/no-such-thing')
        assert resp.status_code == 404
        assert 'no vnc stack' in resp.json()['detail']


class test_create(TestCase):

    def test_create__minimal_body(self):
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.post('/vnc/stack', json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body['instance_id']       == INSTANCE_ID
        assert body['operator_password']                                            # Returned once
        assert body['state']             == 'pending'
        assert svc.last_create_req is not None

    def test_create__with_name_interceptor_choice(self):                            # Nested Interceptor__Choice in body
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.post('/vnc/stack', json={'stack_name': 'vnc-prod',
                                            'interceptor': {'kind': 'name', 'name': 'header_logger'}})
        assert resp.status_code == 200
        assert resp.json()['stack_name'] == 'vnc-prod'
        assert str(svc.last_create_req.interceptor.kind) == 'name'
        assert str(svc.last_create_req.interceptor.name) == 'header_logger'


class test_delete(TestCase):

    def test_delete__hit(self):
        c    = _client(_Fake_Service(hit=True, terminate=True))
        resp = c.delete(f'/vnc/stack/{STACK_NAME}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['target']                  == INSTANCE_ID
        assert body['terminated_instance_ids'] == [INSTANCE_ID]

    def test_delete__miss_returns_404(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.delete('/vnc/stack/no-such-thing')
        assert resp.status_code == 404


class test_health(TestCase):

    def test_health__forwards_creds_to_service(self):
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.get(f'/vnc/stack/{STACK_NAME}/health?username=operator&password=secret')
        assert resp.status_code == 200
        body = resp.json()
        assert body['state']               == 'ready'
        assert body['nginx_ok']            is True
        assert body['mitmweb_ok']          is True
        assert body['flow_count']          == 2
        assert svc.last_health_args[2]     == 'operator'
        assert svc.last_health_args[3]     == 'secret'
