# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__Stack__Service (POD backend)
# Composes the real service but injects an in-memory fake Host_Plane__Client
# for the HTTP boundary. No mocks anywhere — the fake is a subclass with an
# in-memory pod store.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Request import Schema__Playwright__Stack__Create__Request
from sgraph_ai_service_playwright__cli.playwright.service.Host_Plane__Client          import Host_Plane__Client
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Service  import Playwright__Stack__Service, DEFAULT_IMAGE, TYPE_ID


# ── in-memory fake of the host-plane pods API ───────────────────────────────
class _Fake_Host_Plane__Client(Host_Plane__Client):
    pods : dict                                                                     # name → pod dict (the host-plane's world)

    def start_pod(self, name, image, ports, env, type_id):
        self.pods[name] = {'name'      : name                               ,
                           'image'     : image                              ,
                           'status'    : 'running'                          ,
                           'state'     : 'Up 1 second'                      ,
                           'ports'     : {'8000/tcp': [{'HostPort': str(list(ports.values())[0])}]},
                           'created_at': '2026-05-14T00:00:00Z'              ,
                           'type_id'   : type_id                            }
        return {'name': name, 'container_id': f'c-{name}', 'started': True, 'error': ''}

    def list_pods(self):
        return list(self.pods.values())

    def get_pod(self, name):
        return self.pods.get(name)

    def remove_pod(self, name):
        self.pods.pop(name, None)
        return {'name': name, 'removed': True}


class _Service(Playwright__Stack__Service):                                         # service wired to the fake — one shared pod world
    fake : _Fake_Host_Plane__Client

    def host_plane_client(self, host_url, host_api_key):
        return self.fake


class test_Playwright__Stack__Service(TestCase):

    def setUp(self):
        self.fake    = _Fake_Host_Plane__Client(base_url='http://host:19009', api_key='k')
        self.service = _Service(fake=self.fake)

    def _request(self, **kw):
        defaults = dict(host_url='http://host:19009', host_api_key='k', api_key='secret')
        defaults.update(kw)
        return Schema__Playwright__Stack__Create__Request(**defaults)

    # ── create ───────────────────────────────────────────────────────────────
    def test__create_stack__starts_pod_and_returns_running(self):
        response = self.service.create_stack(self._request(stack_name='happy-turing'))
        assert response.started                is True
        assert str(response.stack_name)        == 'happy-turing'
        assert str(response.pod_name)          == 'happy-turing'
        assert str(response.container_id)      == 'c-happy-turing'
        assert response.state                  == Enum__Playwright__Stack__State.RUNNING
        assert str(response.image)             == f'{DEFAULT_IMAGE}:latest'
        assert response.host_port              == 8000
        assert 'happy-turing'                  in self.fake.pods
        assert self.fake.pods['happy-turing']['type_id'] == TYPE_ID

    def test__create_stack__generates_name_when_blank(self):
        response = self.service.create_stack(self._request())
        assert str(response.stack_name)         != ''
        assert '-'                              in str(response.stack_name)          # adjective-scientist
        assert str(response.stack_name)         in self.fake.pods

    def test__create_stack__bakes_api_key_into_pod_env(self):
        self.service.create_stack(self._request(stack_name='keyed', api_key='abc123'))
        # the fake doesn't store env, but the real start_pod path passes it — assert via a probing fake
        captured = {}
        class _Capturing(_Fake_Host_Plane__Client):
            def start_pod(self, name, image, ports, env, type_id):
                captured.update(env)
                return super().start_pod(name, image, ports, env, type_id)
        svc = _Service(fake=_Capturing(base_url='u', api_key='k'))
        svc.create_stack(self._request(stack_name='keyed2', api_key='abc123'))
        assert captured == {'FAST_API__AUTH__API_KEY__VALUE': 'abc123'}

    def test__create_stack__host_plane_error_surfaces_in_response(self):
        class _Broken(_Fake_Host_Plane__Client):
            def start_pod(self, name, image, ports, env, type_id):
                raise ConnectionError('host-plane refused')
        svc      = _Service(fake=_Broken(base_url='u', api_key='k'))
        response = svc.create_stack(self._request(stack_name='doomed'))
        assert response.started is False
        assert response.state   == Enum__Playwright__Stack__State.PENDING
        assert 'host-plane refused' in str(response.error)

    # ── list ─────────────────────────────────────────────────────────────────
    def test__list_stacks__only_returns_playwright_pods(self):
        self.service.create_stack(self._request(stack_name='ours'))
        self.fake.pods['someone-else'] = {'name': 'someone-else', 'image': 'redis',
                                          'status': 'running', 'state': 'Up', 'ports': {},
                                          'created_at': '', 'type_id': 'docker'}
        listing = self.service.list_stacks('http://host:19009', 'k')
        names   = [str(s.stack_name) for s in listing.stacks]
        assert names == ['ours']

    # ── info ─────────────────────────────────────────────────────────────────
    def test__get_stack_info__maps_pod_to_info(self):
        self.service.create_stack(self._request(stack_name='inspect-me', host_port=8123))
        info = self.service.get_stack_info('http://host:19009', 'k', 'inspect-me')
        assert info is not None
        assert str(info.stack_name) == 'inspect-me'
        assert info.state           == Enum__Playwright__Stack__State.RUNNING
        assert info.host_port       == 8123

    def test__get_stack_info__returns_none_on_miss(self):
        assert self.service.get_stack_info('http://host:19009', 'k', 'ghost') is None

    def test__get_stack_info__returns_none_for_non_playwright_pod(self):
        self.fake.pods['redis'] = {'name': 'redis', 'type_id': 'docker', 'status': 'running',
                                   'image': 'redis', 'state': 'Up', 'ports': {}, 'created_at': ''}
        assert self.service.get_stack_info('http://host:19009', 'k', 'redis') is None

    # ── delete ───────────────────────────────────────────────────────────────
    def test__delete_stack__removes_pod(self):
        self.service.create_stack(self._request(stack_name='kill-me'))
        response = self.service.delete_stack('http://host:19009', 'k', 'kill-me')
        assert response.removed         is True
        assert str(response.stack_name) == 'kill-me'
        assert 'kill-me'                not in self.fake.pods

    def test__delete_stack__miss_returns_not_removed(self):
        response = self.service.delete_stack('http://host:19009', 'k', 'ghost')
        assert response.removed is False

    # ── health ───────────────────────────────────────────────────────────────
    def test__health__running_pod(self):
        self.service.create_stack(self._request(stack_name='alive'))
        health = self.service.health('http://host:19009', 'k', 'alive')
        assert health.running is True
        assert health.state   == Enum__Playwright__Stack__State.RUNNING

    def test__health__missing_pod(self):
        health = self.service.health('http://host:19009', 'k', 'ghost')
        assert health.running is False
        assert health.state   == Enum__Playwright__Stack__State.UNKNOWN
        assert 'ghost'        in str(health.error)

    # ── pure mappers ─────────────────────────────────────────────────────────
    def test__map_state(self):
        assert self.service.map_state('running') == Enum__Playwright__Stack__State.RUNNING
        assert self.service.map_state('exited')  == Enum__Playwright__Stack__State.EXITED
        assert self.service.map_state('created') == Enum__Playwright__Stack__State.PENDING
        assert self.service.map_state('weird')   == Enum__Playwright__Stack__State.UNKNOWN

    def test__extract_host_port(self):
        assert self.service.extract_host_port({'8000/tcp': [{'HostPort': '9001'}]}) == 9001
        assert self.service.extract_host_port({'8000/tcp': '9002'})                 == 9002
        assert self.service.extract_host_port({})                                   == 0
