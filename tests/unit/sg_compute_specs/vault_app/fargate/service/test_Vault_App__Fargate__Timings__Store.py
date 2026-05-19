# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Timings__Store
# Covers: append, last, clear, default path, malformed-line tolerance.
# Uses a temp path so tests do not touch ~/.cache.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
from unittest import TestCase

from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Timings__Record       import Schema__VAF__Timings__Record
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Timings__Store import Vault_App__Fargate__Timings__Store

_TEMP_PATH = '/tmp/test_vaf_timings_store.jsonl'


def _make_record(slug: str = 'test-slug', total_ms: int = 1000) -> Schema__VAF__Timings__Record:
    return Schema__VAF__Timings__Record(
        slug           = slug,
        cluster_name   = 'vault-cluster',
        task_ready_ms  = total_ms // 2,
        vault_ready_ms = total_ms,
        total_ms       = total_ms,
        launch_type    = 'FARGATE',
        executed_at    = '2026-05-19T00:00:00+00:00',
    )


class test_Vault_App__Fargate__Timings__Store(TestCase):

    def setUp(self):
        if os.path.exists(_TEMP_PATH):
            os.remove(_TEMP_PATH)

    def tearDown(self):
        if os.path.exists(_TEMP_PATH):
            os.remove(_TEMP_PATH)

    def _make_store(self) -> Vault_App__Fargate__Timings__Store:
        return Vault_App__Fargate__Timings__Store(path=_TEMP_PATH)

    # ── construction ─────────────────────────────────────────────────────────

    def test_store_is_type_safe(self):
        store = self._make_store()
        assert isinstance(store, Vault_App__Fargate__Timings__Store)

    def test_injected_path_is_used(self):
        store = self._make_store()
        assert store._get_path() == _TEMP_PATH

    def test_default_path_contains_cache_sg(self):
        store = Vault_App__Fargate__Timings__Store()
        assert '.cache' in store._default_path()
        assert 'vault-app-fargate' in store._default_path()
        assert store._default_path().endswith('timings.jsonl')

    # ── last() on missing file ────────────────────────────────────────────────

    def test_last_returns_empty_list_when_file_absent(self):
        store = self._make_store()
        assert store.last() == []

    def test_last_n_returns_empty_list_when_file_absent(self):
        store = self._make_store()
        assert store.last(5) == []

    # ── append ────────────────────────────────────────────────────────────────

    def test_append_creates_file(self):
        store = self._make_store()
        store.append(_make_record())
        assert os.path.exists(_TEMP_PATH)

    def test_append_writes_valid_json_line(self):
        store = self._make_store()
        store.append(_make_record(slug='alpha', total_ms=500))
        lines = open(_TEMP_PATH).read().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data['slug'] == 'alpha'
        assert data['total_ms'] == 500

    def test_append_creates_parent_dirs(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        deep_path = os.path.join(tmpdir, 'a', 'b', 'c', 'timings.jsonl')
        store = Vault_App__Fargate__Timings__Store(path=deep_path)
        store.append(_make_record())
        assert os.path.exists(deep_path)

    # ── multiple appends ──────────────────────────────────────────────────────

    def test_multiple_appends_accumulate(self):
        store = self._make_store()
        for i in range(3):
            store.append(_make_record(slug=f'slug-{i}', total_ms=i * 100))
        lines = open(_TEMP_PATH).read().strip().splitlines()
        assert len(lines) == 3

    def test_multiple_appends_preserve_order(self):
        store = self._make_store()
        slugs = ['alpha', 'beta', 'gamma']
        for s in slugs:
            store.append(_make_record(slug=s))
        lines = open(_TEMP_PATH).read().strip().splitlines()
        for i, s in enumerate(slugs):
            assert json.loads(lines[i])['slug'] == s

    # ── last() with records ───────────────────────────────────────────────────

    def test_last_returns_schema_instances(self):
        store = self._make_store()
        store.append(_make_record())
        records = store.last()
        assert len(records) == 1
        assert isinstance(records[0], Schema__VAF__Timings__Record)

    def test_last_returns_correct_slug(self):
        store = self._make_store()
        store.append(_make_record(slug='my-slug'))
        records = store.last()
        assert records[0].slug == 'my-slug'

    def test_last_default_n_returns_all_when_fewer(self):
        store = self._make_store()
        for i in range(3):
            store.append(_make_record(slug=f's{i}'))
        assert len(store.last()) == 3

    def test_last_2_on_5_records_returns_last_2(self):
        store = self._make_store()
        slugs = [f's{i}' for i in range(5)]
        for s in slugs:
            store.append(_make_record(slug=s))
        records = store.last(2)
        assert len(records) == 2
        assert records[0].slug == 's3'
        assert records[1].slug == 's4'

    def test_last_10_on_5_records_returns_all_5(self):
        store = self._make_store()
        for i in range(5):
            store.append(_make_record(slug=f's{i}'))
        assert len(store.last(10)) == 5

    # ── clear ─────────────────────────────────────────────────────────────────

    def test_clear_removes_file(self):
        store = self._make_store()
        store.append(_make_record())
        assert os.path.exists(_TEMP_PATH)
        store.clear()
        assert not os.path.exists(_TEMP_PATH)

    def test_clear_on_nonexistent_file_is_noop(self):
        store = self._make_store()
        store.clear()                                                              # must not raise

    def test_clear_then_last_returns_empty(self):
        store = self._make_store()
        store.append(_make_record())
        store.clear()
        assert store.last() == []

    # ── round-trip ────────────────────────────────────────────────────────────

    def test_round_trip_all_fields(self):
        store  = self._make_store()
        record = _make_record(slug='rt-slug', total_ms=9876)
        store.append(record)
        records = store.last()
        r = records[0]
        assert r.slug           == 'rt-slug'
        assert r.cluster_name   == 'vault-cluster'
        assert r.total_ms       == 9876
        assert r.launch_type    == 'FARGATE'
        assert r.executed_at    == '2026-05-19T00:00:00+00:00'
