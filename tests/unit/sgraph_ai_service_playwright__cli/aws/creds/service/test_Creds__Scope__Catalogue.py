# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Creds__Scope__Catalogue (in-memory)
# No mocks. No patches. Uses Creds__Scope__Catalogue__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue__In_Memory import (
    Creds__Scope__Catalogue__In_Memory,
)


class Test__Creds__Scope__Catalogue:

    def test_1__load_empty_catalogue(self):
        cat  = Creds__Scope__Catalogue__In_Memory()
        data = cat.load()
        assert data == {'scopes': {}}

    def test_2__scope_add_returns_entry(self):
        cat   = Creds__Scope__Catalogue__In_Memory()
        entry = cat.scope_add('dev', 'arn:aws:iam::123456789012:role/Dev', '2h')
        assert entry['name']     == 'dev'
        assert entry['role_arn'] == 'arn:aws:iam::123456789012:role/Dev'
        assert entry['max_ttl']  == '2h'
        assert entry['created_at'] != ''

    def test_3__scope_get_existing(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('staging', 'arn:aws:iam::123456789012:role/Staging')
        got = cat.scope_get('staging')
        assert got is not None
        assert got['name'] == 'staging'

    def test_4__scope_get_missing_returns_none(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        assert cat.scope_get('does-not-exist') is None

    def test_5__scope_list_sorted(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('zulu',  'arn:aws:iam::1:role/Z')
        cat.scope_add('alpha', 'arn:aws:iam::1:role/A')
        cat.scope_add('mike',  'arn:aws:iam::1:role/M')
        scopes = cat.scope_list()
        assert [s['name'] for s in scopes] == ['alpha', 'mike', 'zulu']

    def test_6__scope_remove_existing(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('temp', 'arn:aws:iam::1:role/T')
        ok = cat.scope_remove('temp')
        assert ok is True
        assert cat.scope_get('temp') is None

    def test_7__scope_remove_missing_returns_false(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        assert cat.scope_remove('never-existed') is False

    def test_8__scope_add_overwrites_existing(self):
        cat = Creds__Scope__Catalogue__In_Memory()
        cat.scope_add('prod', 'arn:aws:iam::1:role/Old')
        cat.scope_add('prod', 'arn:aws:iam::1:role/New')
        got = cat.scope_get('prod')
        assert got['role_arn'] == 'arn:aws:iam::1:role/New'
        assert len(cat.scope_list()) == 1
