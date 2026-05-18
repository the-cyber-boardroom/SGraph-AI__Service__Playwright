# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_Publish__Service
# register / unpublish / status / list — all against in-memory fakes.
# No mocks, no patches, no AWS calls, no SSM.
#
# The fakes use a SHARED ec2_store dict so the slug registry (EC2 tags) and
# the fake vault-app stay consistent — registering a slug seeds an instance
# in the store, and unpublish removes it.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone
from types    import SimpleNamespace

from sg_compute_specs.vault_publish.schemas.Enum__Vault_Publish__State          import Enum__Vault_Publish__State
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                      import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key                import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request  import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.service.Slug__Registry                      import (
    Slug__Registry, TAG_STYPE, STYPE_VAL,
)
from sg_compute_specs.vault_publish.service.Vault_Publish__Service              import Vault_Publish__Service
from sg_compute_specs.vault_publish.tests.test_Slug__Registry                   import _Fake_EC2


# ── Fake vault-app that seeds the shared EC2 store ────────────────────────────

class _Fake_Vault_App:
    def __init__(self, ec2_store: dict,
                 state: str = 'running', public_ip: str = '1.2.3.4'):
        self._store     = ec2_store
        self._state     = state
        self._public_ip = public_ip
        self._next_id   = 0
        self.created    = []
        self.deleted    = []

    def _new_iid(self) -> str:
        self._next_id += 1
        return f'i-fake{self._next_id:03d}'

    def create_stack(self, req):
        self.created.append(req)
        iid = self._new_iid()
        self._store[iid] = {
            'tags'       : {TAG_STYPE: STYPE_VAL, 'StackName': req.stack_name},
            'state'      : self._state,
            'public_ip'  : self._public_ip,
            'launch_time': datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
        }
        return SimpleNamespace(stack_info=SimpleNamespace(
            stack_name=req.stack_name, instance_id=iid))

    def delete_stack(self, region, stack_name):
        self.deleted.append((region, stack_name))
        for iid, inst in list(self._store.items()):
            if inst['tags'].get('StackName') == stack_name:
                del self._store[iid]

    def get_stack_info(self, region, stack_name):
        for inst in self._store.values():
            if inst['tags'].get('StackName') == stack_name:
                return SimpleNamespace(
                    state      = inst['state'],
                    public_ip  = inst['public_ip'],
                    vault_url  = f'http://{inst["public_ip"]}:8080',
                    stack_name = stack_name,
                )
        return None


# ── Build wired service ────────────────────────────────────────────────────────

def _build_svc(state: str = 'running', public_ip: str = '1.2.3.4'):
    ec2_store = {}
    reg = Slug__Registry(region='eu-west-2')
    reg._ec2_factory = lambda r: _Fake_EC2(ec2_store)
    fake_va = _Fake_Vault_App(ec2_store, state=state, public_ip=public_ip)
    svc = Vault_Publish__Service().setup()
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
        assert str(resp.slug)    == 'sara-cv'
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
        assert reg.get('sara-cv') is None              # vault-app removed the instance → tags gone
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
        svc, _, _ = _build_svc(state='running', public_ip='1.2.3.4')
        svc.register(_register_req())
        resp = svc.status('sara-cv')
        assert resp.state     == Enum__Vault_Publish__State.RUNNING
        assert resp.public_ip == '1.2.3.4'
        assert 'sara-cv' in str(resp.slug)

    def test_status_stopped(self):
        svc, _, _ = _build_svc(state='stopped', public_ip='')
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
        slugs = sorted(str(e.slug) for e in resp.entries)
        assert slugs == ['slug-a', 'slug-b']

    def test_list_redacts_vault_keys(self):
        svc, _, _ = _build_svc()
        svc.register(_register_req(vault_key='my-secret-key'))
        resp = svc.list_slugs()
        for entry in resp.entries:
            assert str(getattr(entry, 'vault_key', '') or '') == ''
