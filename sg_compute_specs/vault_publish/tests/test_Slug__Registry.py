# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Slug__Registry
# In-memory Parameter-like fake injected via _param_factory seam.
# No mocks, no patches. No SSM calls.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sg_compute_specs.vault_publish.service.Slug__Registry import Slug__Registry, SSM_PREFIX


# ── In-memory Parameter fake ──────────────────────────────────────────────────

class _Param__In_Memory:
    """Shared dict-backed parameter store. name=None returns the index proxy."""

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


def _make_registry(store: dict = None) -> tuple:
    if store is None:
        store = {}
    reg = Slug__Registry()
    reg._param_factory = lambda name: _Param__In_Memory(store, name)
    return reg, store


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSlugRegistry:
    def test_put_and_get(self):
        reg, _ = _make_registry()
        ok  = reg.put(slug='sara-cv', stack_name='sara-cv',
                      fqdn='sara-cv.aws.sg-labs.app', region='eu-west-2')
        assert ok is True
        entry = reg.get('sara-cv')
        assert entry is not None
        assert str(entry.slug)       == 'sara-cv'
        assert str(entry.stack_name) == 'sara-cv'
        assert str(entry.fqdn)       == 'sara-cv.aws.sg-labs.app'
        assert str(entry.region)     == 'eu-west-2'
        assert entry.created_at      != ''

    def test_no_vault_key_in_ssm(self):
        # SECURITY: vault_key must NEVER appear in SSM payload.
        reg, store = _make_registry()
        reg.put(slug='sara-cv', stack_name='sara-cv',
                fqdn='sara-cv.aws.sg-labs.app', region='eu-west-2')
        raw = store[f'{SSM_PREFIX}/sara-cv']
        data = json.loads(raw)
        assert 'vault_key' not in data, 'vault_key leaked into SSM payload'

    def test_get_missing_returns_none(self):
        reg, _ = _make_registry()
        assert reg.get('nonexistent') is None

    def test_delete(self):
        reg, _ = _make_registry()
        reg.put(slug='test', stack_name='test',
                fqdn='test.aws.sg-labs.app', region='eu-west-2')
        assert reg.get('test') is not None
        ok = reg.delete('test')
        assert ok is True
        assert reg.get('test') is None

    def test_delete_missing_returns_false(self):
        reg, _ = _make_registry()
        assert reg.delete('nonexistent') is False

    def test_list_all_empty(self):
        reg, _ = _make_registry()
        assert reg.list_all() == []

    def test_list_all_with_entries(self):
        reg, _ = _make_registry()
        reg.put(slug='slug-a', stack_name='slug-a',
                fqdn='slug-a.aws.sg-labs.app', region='eu-west-2')
        reg.put(slug='slug-b', stack_name='slug-b',
                fqdn='slug-b.aws.sg-labs.app', region='eu-west-2')
        slugs = reg.list_all()
        assert len(slugs) == 2
        assert 'slug-a' in slugs
        assert 'slug-b' in slugs

    def test_overwrite_existing(self):
        reg, _ = _make_registry()
        reg.put(slug='test', stack_name='test',
                fqdn='test.aws.sg-labs.app', region='eu-west-2')
        reg.put(slug='test', stack_name='test',
                fqdn='test.aws.sg-labs.app', region='us-east-1')
        entry = reg.get('test')
        assert str(entry.region) == 'us-east-1'
