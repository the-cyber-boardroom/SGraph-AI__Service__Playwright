# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sg__Aws__Session (v0.2.28 additions)
# _session_name pattern, from_context(), boto3_client_from_context(),
# account_id_for() cache hit + miss (no real STS calls).
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Account_Id        import Safe_Str__AWS__Account_Id
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region            import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN         import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                    import Sg__Aws__Session, _session_name
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context                    import Sg__Aws__Context
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                  import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS                    import Keyring__Mac__OS__In_Memory

SESSION_NAME_RE = re.compile(r'^sg-[a-zA-Z0-9\-]+-\d+-[0-9a-f]{8}$')

SESSION_NAME_RE = re.compile(r'^sg-[a-zA-Z0-9\-]+-\d+-[0-9a-f]{8}$')


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, account_id: str = '') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name    (name)          ,
        region          = Safe_Str__AWS__Region   ('us-east-1')   ,
        assume_role_arn = Safe_Str__AWS__Role__ARN('')             ,
        session_name    = Safe_Str__Role__Name    (f'sg-{name}')  ,
        account_id      = Safe_Str__AWS__Account_Id(account_id)   ,
    )


class test__session_name(TestCase):

    def test__session_name_matches_pattern(self):           # sg-<role>-<ts>-<8hex>
        name = _session_name('admin')
        assert SESSION_NAME_RE.match(name), f'unexpected pattern: {name!r}'

    def test__session_name_starts_with_sg(self):
        assert _session_name('dev').startswith('sg-')

    def test__session_name_contains_role(self):
        assert 'admin' in _session_name('admin')

    def test__session_name_at_most_64_chars(self):          # IAM SessionName hard limit
        long_role = 'a' * 60
        assert len(_session_name(long_role)) <= 64

    def test__session_name_replaces_spaces(self):
        name = _session_name('my role')
        assert ' ' not in name


class test_Sg__Aws__Session__from_context(TestCase):

    def test__from_context_returns_session_instance(self):
        Sg__Aws__Context.clear_global_role()
        session = Sg__Aws__Session.from_context()
        assert isinstance(session, Sg__Aws__Session)

    def test__from_context_no_role_returns_unconfigured_session(self):
        Sg__Aws__Context.clear_global_role()
        session = Sg__Aws__Session.from_context()
        assert session.store is not None

    def test__from_context_isolates_store_per_call(self):
        s1 = Sg__Aws__Session.from_context()
        s2 = Sg__Aws__Session.from_context()
        assert s1 is not s2                                  # two independent session objects


class test_Sg__Aws__Session__boto3_client_from_context(TestCase):

    def test__no_role_falls_through_to_bare_boto3(self):
        Sg__Aws__Context.clear_global_role()
        store   = _store()
        session = Sg__Aws__Session(store=store)
        client  = session.boto3_client_from_context('sts')  # no role → bare boto3 client
        assert client is not None                            # boto3.client() always returns an object

    def test__unknown_role_falls_through_to_bare_boto3(self):
        Sg__Aws__Context.set_global_role('nonexistent-role-xyz')
        store   = _store()
        session = Sg__Aws__Session(store=store)
        client  = session.boto3_client_from_context('sts')  # role not in store → fall-through
        assert client is not None
        Sg__Aws__Context.clear_global_role()

    def test__region_passed_to_bare_boto3_client(self):
        Sg__Aws__Context.clear_global_role()
        store   = _store()
        session = Sg__Aws__Session(store=store)
        client  = session.boto3_client_from_context('sts', region='eu-west-1')
        assert client is not None                            # just verifies no crash with region kwarg


class test_Sg__Aws__Session__account_id_for(TestCase):

    def test__returns_cached_account_id(self):               # no STS call when account_id already stored
        store = _store()
        store.role_set(_cfg('dev', account_id='123456789012'))
        store.aws_credentials_set('dev', 'AKIAIOSFODNN7EXAMPLE', 'secret')
        session = Sg__Aws__Session(store=store)
        assert session.account_id_for('dev') == '123456789012'

    def test__unknown_role_returns_empty(self):
        store   = _store()
        session = Sg__Aws__Session(store=store)
        assert session.account_id_for('nonexistent') == ''

    def test__no_credentials_returns_empty(self):            # role config exists but no AWS creds → can't call STS
        store = _store()
        store.role_set(_cfg('dev'))                          # no account_id cached
        session = Sg__Aws__Session(store=store)
        assert session.account_id_for('dev') == ''           # boto3_client returns None → '' gracefully

    def test__account_id_from_context_no_role_returns_empty(self):
        Sg__Aws__Context.clear_global_role()
        assert Sg__Aws__Session.account_id_from_context() == ''

    def test__account_id_persisted_in_store_after_roundtrip(self):
        store = _store()
        store.role_set(_cfg('prod', account_id='999888777666'))
        store.aws_credentials_set('prod', 'AKIAIOSFODNN7EXAMPLE', 'secret')
        session = Sg__Aws__Session(store=store)
        result  = session.account_id_for('prod')
        assert result == '999888777666'
        config  = store.role_get('prod')
        assert str(config.account_id) == '999888777666'      # still present after read-back
