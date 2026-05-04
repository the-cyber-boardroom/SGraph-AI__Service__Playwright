# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Routes__Prometheus__Stack
# Real subclass overrides the Prometheus__Service methods to return scripted
# Type_Safe responses. No mocks. Wires the routes onto a Fast_API app and
# drives them via the FastAPI TestClient.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional
from unittest                                                                       import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Stack__Info import List__Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.fast_api.routes.Routes__Prometheus__Stack import Routes__Prometheus__Stack
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request  import Schema__Prom__Stack__Create__Request
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Response import Schema__Prom__Stack__Create__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Delete__Response import Schema__Prom__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__List import Schema__Prom__Stack__List
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Service       import Prometheus__Service


STACK_NAME  = 'prom-quiet-fermi'
INSTANCE_ID = 'i-0123456789abcdef0'


def _info():
    return Schema__Prom__Stack__Info(stack_name        = STACK_NAME              ,
                                      aws_name_tag      = 'prometheus-quiet-fermi',
                                      instance_id       = INSTANCE_ID             ,
                                      region            = 'eu-west-2'             ,
                                      public_ip         = '5.6.7.8'               ,
                                      prometheus_url    = 'http://5.6.7.8:9090/'  ,
                                      state             = Enum__Prom__Stack__State.RUNNING)


def _create_response(stack_name: str = STACK_NAME):
    return Schema__Prom__Stack__Create__Response(stack_name        = stack_name                  ,
                                                   aws_name_tag      = f'prometheus-{stack_name}'  ,
                                                   instance_id       = INSTANCE_ID                  ,
                                                   region            = 'eu-west-2'                  ,
                                                   targets_count     = 0                            ,
                                                   state             = Enum__Prom__Stack__State.PENDING)


class _Fake_Service(Prometheus__Service):                                            # Real subclass — overrides only the public methods
    def __init__(self, hit: bool = True, terminate: bool = True):
        super().__init__()
        self.hit              = hit
        self.terminate        = terminate
        self.last_create_req  : Optional[Schema__Prom__Stack__Create__Request] = None
        self.last_health_args : Optional[tuple]                                = None

    def list_stacks(self, region: str) -> Schema__Prom__Stack__List:
        stacks = List__Schema__Prom__Stack__Info()
        if self.hit:
            stacks.append(_info())
        return Schema__Prom__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Prom__Stack__Info]:
        return _info() if self.hit else None

    def create_stack(self, request, creator: str = '') -> Schema__Prom__Stack__Create__Response:
        self.last_create_req = request
        return _create_response(str(request.stack_name) or STACK_NAME)

    def delete_stack(self, region: str, stack_name: str) -> Schema__Prom__Stack__Delete__Response:
        if not self.hit:
            return Schema__Prom__Stack__Delete__Response()                          # Empty fields ⇒ 404
        terminated = List__Instance__Id()
        if self.terminate:
            terminated.append(INSTANCE_ID)
        return Schema__Prom__Stack__Delete__Response(target=INSTANCE_ID, stack_name=stack_name, terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str, username: str = '', password: str = '') -> Schema__Prom__Health:
        self.last_health_args = (region, stack_name, username, password)
        return Schema__Prom__Health(stack_name=stack_name, state=Enum__Prom__Stack__State.READY,
                                     prometheus_ok=True, targets_total=3, targets_up=2)


def _client(service: _Fake_Service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Prometheus__Stack, service=service)
    return app.client()


class test_list_and_info(TestCase):

    def test_list__non_empty(self):
        c    = _client(_Fake_Service(hit=True))
        resp = c.get('/prometheus/stacks')
        assert resp.status_code == 200
        body = resp.json()
        assert body['region']                      == 'eu-west-2'
        assert len(body['stacks'])                 == 1
        assert body['stacks'][0]['stack_name']     == STACK_NAME

    def test_list__empty(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.get('/prometheus/stacks')
        assert resp.status_code == 200
        assert resp.json()['stacks'] == []

    def test_info__hit(self):
        c    = _client(_Fake_Service(hit=True))
        resp = c.get(f'/prometheus/stack/{STACK_NAME}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['instance_id']    == INSTANCE_ID
        assert body['prometheus_url'] == 'http://5.6.7.8:9090/'
        assert body['state']          == 'running'

    def test_info__miss_returns_404(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.get('/prometheus/stack/no-such-thing')
        assert resp.status_code == 404
        assert 'no prometheus stack' in resp.json()['detail']


class test_create(TestCase):

    def test_create__minimal_body(self):
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.post('/prometheus/stack', json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body['instance_id']  == INSTANCE_ID
        assert body['state']        == 'pending'
        assert body['targets_count'] == 0
        assert svc.last_create_req is not None

    def test_create__pinned_stack_name_passes_through(self):
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.post('/prometheus/stack', json={'stack_name': 'prom-prod'})
        assert resp.status_code == 200
        assert resp.json()['stack_name'] == 'prom-prod'


class test_delete(TestCase):

    def test_delete__hit(self):
        c    = _client(_Fake_Service(hit=True, terminate=True))
        resp = c.delete(f'/prometheus/stack/{STACK_NAME}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['target']                  == INSTANCE_ID
        assert body['terminated_instance_ids'] == [INSTANCE_ID]

    def test_delete__miss_returns_404(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.delete('/prometheus/stack/no-such-thing')
        assert resp.status_code == 404


class test_health(TestCase):

    def test_health__forwards_creds_to_service(self):
        svc  = _Fake_Service()
        c    = _client(svc)
        resp = c.get(f'/prometheus/stack/{STACK_NAME}/health?username=ops&password=secret')
        assert resp.status_code            == 200
        body = resp.json()
        assert body['state']               == 'ready'
        assert body['prometheus_ok']       is True
        assert body['targets_total']       == 3
        assert body['targets_up']          == 2
        assert svc.last_health_args[2]     == 'ops'
        assert svc.last_health_args[3]     == 'secret'
