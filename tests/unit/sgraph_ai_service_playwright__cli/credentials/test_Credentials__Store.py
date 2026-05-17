# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Store
#
# Uses Keyring__Mac__OS__In_Memory — no system keyring required.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, region: str = 'us-east-1', arn: str = '', session: str = '') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name)         ,
        region          = Safe_Str__AWS__Region(region)      ,
        assume_role_arn = Safe_Str__AWS__Role__ARN(arn)      ,
        session_name    = Safe_Str__Role__Name(session or f'sg-{name}'),
    )


class test_Credentials__Store__roles(TestCase):

    def test_role_set_and_get(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        cfg = store.role_get('default')
        assert cfg is not None
        assert str(cfg.region) == 'us-east-1'
        assert str(cfg.assume_role_arn) == ''

    def test_role_list(self):
        store = _store()
        store.role_set(_cfg('admin',   'eu-west-1'))
        store.role_set(_cfg('default', 'us-east-1'))
        assert store.role_list() == ['admin', 'default']

    def test_role_delete(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        result = store.role_delete('default')
        assert result is True
        assert store.role_get('default') is None

    def test_role_get_missing_returns_none(self):
        store = _store()
        assert store.role_get('no-such-role') is None

    def test_role_set_with_assume_role(self):
        store = _store()
        store.role_set(_cfg('admin', 'eu-west-2',
                            arn='arn:aws:iam::123456789012:role/sg-admin',
                            session='sg-session'))
        cfg = store.role_get('admin')
        assert str(cfg.assume_role_arn) == 'arn:aws:iam::123456789012:role/sg-admin'
        assert str(cfg.session_name)    == 'sg-session'


class test_Credentials__Store__aws_credentials(TestCase):

    def test_aws_credentials_set_and_get(self):
        store = _store()
        store.aws_credentials_set('default', 'AKIAIOSFODNN7EXAMPLE', 's3cr3t')
        creds = store.aws_credentials_get('default')
        assert creds is not None
        assert str(creds.access_key) == 'AKIAIOSFODNN7EXAMPLE'
        assert str(creds.secret_key) == 's3cr3t'

    def test_aws_credentials_missing_returns_none(self):
        store = _store()
        assert store.aws_credentials_get('no-role') is None

    def test_aws_credentials_delete(self):
        store = _store()
        store.aws_credentials_set('default', 'AKIA...', 'secret')
        assert store.aws_credentials_delete('default') is True
        assert store.aws_credentials_get('default')    is None


class test_Credentials__Store__vault_keys(TestCase):

    def test_vault_key_set_and_get(self):
        store = _store()
        store.vault_key_set('my-vault', 'super-secret-key')
        assert store.vault_key_get('my-vault') == 'super-secret-key'

    def test_vault_key_list(self):
        store = _store()
        store.vault_key_set('alpha', 'k1')
        store.vault_key_set('beta',  'k2')
        assert store.vault_key_list() == ['alpha', 'beta']

    def test_vault_key_delete(self):
        store = _store()
        store.vault_key_set('my-vault', 'key')
        assert store.vault_key_delete('my-vault') is True
        assert store.vault_key_get('my-vault')    is None


class test_Credentials__Store__secrets(TestCase):

    def test_secret_set_and_get(self):
        store = _store()
        store.secret_set('my-ns', 'db-password', 'hunter2')
        assert store.secret_get('my-ns', 'db-password') == 'hunter2'

    def test_secret_list(self):
        store = _store()
        store.secret_set('my-ns', 'pw1', 'v1')
        store.secret_set('my-ns', 'pw2', 'v2')
        assert sorted(store.secret_list('my-ns')) == ['pw1', 'pw2']

    def test_secret_delete(self):
        store = _store()
        store.secret_set('my-ns', 'pw', 'v')
        assert store.secret_delete('my-ns', 'pw') is True
        assert store.secret_get('my-ns', 'pw')    is None


class test_Credentials__Store__routes(TestCase):

    def test_routes_get_empty_when_none(self):
        store = _store()
        assert store.routes_get() == []

    def test_route_add_and_get(self):
        store = _store()
        store.route_add('aws lambda *', 'lambda-role')
        rules = store.routes_get()
        assert any(r.get('pattern') == 'aws lambda *' and r.get('role') == 'lambda-role'
                   for r in rules)

    def test_route_delete(self):
        store = _store()
        store.route_add('aws s3 *', 's3-role')
        assert store.route_delete('aws s3 *') is True
        rules = store.routes_get()
        assert not any(r.get('pattern') == 'aws s3 *' for r in rules)

    def test_route_delete_missing_returns_false(self):
        store = _store()
        assert store.route_delete('no-such-pattern') is False
