# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Store (Phase B)
# Uses in-memory keyring — no real Keychain calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region           import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN        import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name            import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Credentials           import Schema__AWS__Credentials
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config          import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                 import Credentials__Store
from tests.unit.sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS__In_Memory import Keyring__Mac__OS__In_Memory


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _config(name: str = 'admin', region: str = 'us-east-1', arn: str = '') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name)         ,
        region          = Safe_Str__AWS__Region(region)      ,
        assume_role_arn = Safe_Str__AWS__Role__ARN(arn)      ,
        session_name    = Safe_Str__Role__Name(f'sg-{name}') ,
    )


class test_Credentials__Store__role_config(TestCase):

    def test__role_get_unknown_returns_none(self):
        store  = _store()
        result = store.role_get('nonexistent')
        assert result is None

    def test__role_set_then_get_round_trips(self):
        store  = _store()
        config = _config('admin', 'eu-west-2')
        ok     = store.role_set(config)
        assert ok is True
        loaded = store.role_get('admin')
        assert loaded is not None
        assert str(loaded.name)   == 'admin'
        assert str(loaded.region) == 'eu-west-2'

    def test__role_set_with_arn(self):
        store  = _store()
        config = _config('prod', 'us-east-1', 'arn:aws:iam::123456789012:role/ProdRole')
        store.role_set(config)
        loaded = store.role_get('prod')
        assert 'arn:aws:iam' in str(loaded.assume_role_arn)     # ARN preserved (Safe_Str allows uppercase)

    def test__role_list_empty_returns_empty(self):
        store = _store()
        roles = store.role_list()
        assert roles == []

    def test__role_list_returns_all_set_roles(self):
        store = _store()
        store.role_set(_config('admin'))
        store.role_set(_config('dev'))
        roles = store.role_list()
        assert set(roles) == {'admin', 'dev'}

    def test__role_delete_removes_config(self):
        store = _store()
        store.role_set(_config('admin'))
        store.role_delete('admin')
        assert store.role_get('admin') is None


class test_Credentials__Store__aws_credentials(TestCase):

    def test__aws_credentials_get_unknown_returns_none(self):
        store  = _store()
        result = store.aws_credentials_get('unknown-role')
        assert result is None

    def test__aws_credentials_set_then_get(self):
        store = _store()
        ok    = store.aws_credentials_set('admin', 'AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY')
        assert ok is True
        creds = store.aws_credentials_get('admin')
        assert creds is not None
        assert isinstance(creds, Schema__AWS__Credentials)
        assert str(creds.access_key) == 'AKIAIOSFODNN7EXAMPLE'

    def test__aws_credentials_secret_key_repr_is_redacted(self):
        store = _store()
        store.aws_credentials_set('admin', 'AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY')
        creds = store.aws_credentials_get('admin')
        assert repr(creds.secret_key) == '****'

    def test__aws_credentials_delete_removes_entries(self):
        store = _store()
        store.aws_credentials_set('admin', 'AKID', 'SAK')
        store.aws_credentials_delete('admin')
        assert store.aws_credentials_get('admin') is None

    def test__different_roles_have_independent_credentials(self):
        store = _store()
        store.aws_credentials_set('admin', 'AKIDADMIN', 'SAKADMIN')
        store.aws_credentials_set('dev',   'AKIDDEV',   'SAKDEV')
        admin = store.aws_credentials_get('admin')
        dev   = store.aws_credentials_get('dev')
        assert str(admin.access_key) == 'AKIDADMIN'
        assert str(dev.access_key)   == 'AKIDDEV'


class test_Credentials__Store__vault(TestCase):

    def test__vault_get_unknown_returns_none(self):
        store  = _store()
        result = store.vault_get('myvault')
        assert result is None

    def test__vault_set_then_get(self):
        store = _store()
        ok    = store.vault_set('myvault', 'super-secret-key')
        assert ok is True
        val   = store.vault_get('myvault')
        assert val == 'super-secret-key'

    def test__vault_delete(self):
        store = _store()
        store.vault_set('myvault', 'key')
        store.vault_delete('myvault')
        assert store.vault_get('myvault') is None


class test_Credentials__Store__routes(TestCase):

    def test__routes_get_empty_returns_empty_list(self):
        store  = _store()
        routes = store.routes_get()
        assert routes == []

    def test__routes_set_then_get_round_trips(self):
        store  = _store()
        routes = [{'from': 'dev', 'to': 'prod'}, {'from': 'local', 'to': 'staging'}]
        ok     = store.routes_set(routes)
        assert ok is True
        loaded = store.routes_get()
        assert loaded == routes

    def test__routes_set_overwrites_previous(self):
        store  = _store()
        store.routes_set([{'from': 'a', 'to': 'b'}])
        store.routes_set([{'from': 'x', 'to': 'y'}])
        loaded = store.routes_get()
        assert loaded == [{'from': 'x', 'to': 'y'}]
