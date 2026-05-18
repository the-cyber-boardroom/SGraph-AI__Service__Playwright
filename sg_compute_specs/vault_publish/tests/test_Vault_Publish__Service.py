# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_Publish__Service
# register / unpublish / status / list — all against in-memory fakes.
# No mocks, no patches, no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_publish.schemas.Enum__Vault_Publish__State          import Enum__Vault_Publish__State
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                      import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key                import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request  import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.service.Slug__Registry                      import Slug__Registry
from sg_compute_specs.vault_publish.service.Vault_Publish__Service              import Vault_Publish__Service


# ── In-memory Parameter fake (reused from test_Slug__Registry) ─────────────────

class _Param__In_Memory:
    def __init__(self, store: dict, name: str = None):
        self._store = store
        self._name  = name

    def put(self, value, **_):
        self._store[self._name] = value

    def value(self):
        return self._store.get(self._name)

    def delete(self):
        if self._name not in self._store:
            return False
        del self._store[self._name]
        return True

    def list_under_prefix(self, prefix: str):
        return [{'Name': k} for k in self._store if k.startswith(prefix + '/')]


def _make_registry(store: dict = None) -> Slug__Registry:
    if store is None:
        store = {}
    reg = Slug__Registry()
    reg._param_factory = lambda name: _Param__In_Memory(store, name)
    return reg


# ── Fake vault-app stack info ─────────────────────────────────────────────────

class _Fake_Stack_Info:
    def __init__(self, state='running', public_ip='1.2.3.4', vault_url='http://1.2.3.4:8080',
                 stack_name='sara-cv'):
        self.state       = state
        self.public_ip   = public_ip
        self.vault_url   = vault_url
        self.stack_name  = stack_name

class _Fake_Create_Response:
    class _FakeInfo:
        stack_name = 'sara-cv'
    stack_info = _FakeInfo()

class _Fake_Vault_App:
    def __init__(self, stack_info=None):
        self.created    = []
        self.deleted    = []
        self._info      = stack_info or _Fake_Stack_Info()

    def create_stack(self, req):
        self.created.append(req)
        return _Fake_Create_Response()

    def delete_stack(self, region, stack_name):
        self.deleted.append((region, stack_name))

    def get_stack_info(self, region, stack_name):
        return self._info


# ── Build wired service ────────────────────────────────────────────────────────

def _build_svc(store: dict = None, stack_info=None):
    store    = store or {}
    reg      = _make_registry(store)
    fake_va  = _Fake_Vault_App(stack_info=stack_info)
    svc      = Vault_Publish__Service().setup()
    svc._registry_factory  = lambda: reg
    svc._vault_app_factory = lambda: fake_va
    return svc, reg, fake_va


def _register_req(slug='sara-cv', vault_key='vk-abc', region='eu-west-2'):
    return Schema__Vault_Publish__Register__Request(
        slug      = Safe_Str__Slug(slug),
        vault_key = Safe_Str__Vault__Key(vault_key),
        region    = region)


# ── Tests: register ───────────────────────────────────────────────────────────

class TestVaultPublishServiceRegister:
    def test_register_happy_path(self):
        svc, reg, va = _build_svc()
        resp = svc.register(_register_req())
        assert str(resp.slug)  == 'sara-cv'
        assert 'aws.sg-labs.app' in resp.fqdn
        assert resp.stack_name   != ''
        assert resp.message      == 'registered'
        assert len(va.created)   == 1
        entry = reg.get('sara-cv')
        assert entry is not None
        assert 'sara-cv' in str(entry.fqdn)

    def test_register_sets_fqdn_from_zone(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
        svc, _, _ = _build_svc()
        resp = svc.register(_register_req(slug='test-slug'))
        assert resp.fqdn == 'test-slug.aws.sg-labs.app'

    def test_register_invalid_slug_rejected(self):
        svc, _, va = _build_svc()
        req  = Schema__Vault_Publish__Register__Request(
            slug      = Safe_Str__Slug('www'),
            vault_key = Safe_Str__Vault__Key('vk'),
            region    = 'eu-west-2')
        resp = svc.register(req)
        assert 'invalid slug' in resp.message
        assert len(va.created) == 0

    def test_register_duplicate_slug_rejected(self):
        svc, _, va = _build_svc()
        svc.register(_register_req())
        resp = svc.register(_register_req())
        assert 'already registered' in resp.message
        assert len(va.created) == 1  # second create NOT called


# ── Tests: unpublish ──────────────────────────────────────────────────────────

class TestVaultPublishServiceUnpublish:
    def test_unpublish_happy_path(self):
        svc, reg, va = _build_svc()
        svc.register(_register_req())
        resp = svc.unpublish('sara-cv')
        assert resp.deleted     is True
        assert resp.stack_name  == 'sara-cv'
        assert reg.get('sara-cv') is None
        assert len(va.deleted) == 1

    def test_unpublish_not_found(self):
        svc, _, va = _build_svc()
        resp = svc.unpublish('nonexistent')
        assert resp.deleted     is False
        assert 'not found' in resp.message
        assert len(va.deleted)  == 0


# ── Tests: status ─────────────────────────────────────────────────────────────

class TestVaultPublishServiceStatus:
    def test_status_running(self):
        svc, _, _ = _build_svc(stack_info=_Fake_Stack_Info(state='running'))
        svc.register(_register_req())
        resp = svc.status('sara-cv')
        assert resp.state     == Enum__Vault_Publish__State.RUNNING
        assert resp.public_ip == '1.2.3.4'
        assert 'sara-cv' in str(resp.slug)

    def test_status_stopped(self):
        svc, _, _ = _build_svc(stack_info=_Fake_Stack_Info(state='stopped', public_ip=''))
        svc.register(_register_req())
        resp = svc.status('sara-cv')
        assert resp.state == Enum__Vault_Publish__State.STOPPED

    def test_status_not_registered_returns_unknown(self):
        svc, _, _ = _build_svc()
        resp = svc.status('missing-slug')
        assert resp.state == Enum__Vault_Publish__State.UNKNOWN


# ── Tests: list_slugs ─────────────────────────────────────────────────────────

class TestVaultPublishServiceList:
    def test_list_empty(self):
        svc, _, _ = _build_svc()
        resp = svc.list_slugs()
        assert resp.total == 0

    def test_list_with_entries(self):
        svc, _, _ = _build_svc()
        svc.register(_register_req(slug='slug-a', vault_key='k1'))
        svc.register(_register_req(slug='slug-b', vault_key='k2'))
        resp = svc.list_slugs()
        assert resp.total == 2
        slugs = [str(e.slug) for e in resp.entries]
        assert 'slug-a' in slugs
        assert 'slug-b' in slugs

    def test_list_redacts_vault_keys(self):
        svc, _, _ = _build_svc()
        svc.register(_register_req(vault_key='my-secret-key'))
        resp = svc.list_slugs()
        for entry in resp.entries:
            assert str(getattr(entry, 'vault_key', '') or '') == ''
