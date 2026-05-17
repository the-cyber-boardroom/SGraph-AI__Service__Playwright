# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Resolver (v0.2.28)
# Dry-run resolver: trace() resolves role and chain without any AWS calls.
# Uses in-memory keyring — no real macOS Keychain access.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region            import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN         import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Resolver               import Credentials__Resolver
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store                  import Credentials__Store
from tests.unit.sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS__In_Memory import Keyring__Mac__OS__In_Memory


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _resolver(store: Credentials__Store = None) -> Credentials__Resolver:
    if store is None:
        store = _store()
    return Credentials__Resolver(store=store)


def _add_role(store: Credentials__Store, name: str, arn: str = '', region: str = 'us-east-1') -> None:
    config = Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name)           ,
        region          = Safe_Str__AWS__Region(region)        ,
        assume_role_arn = Safe_Str__AWS__Role__ARN(arn)        ,
        session_name    = Safe_Str__Role__Name(f'sg-{name}')   ,
    )
    store.role_set(config)
    store.aws_credentials_set(name, 'AKIAXXXXXXXXXXXXXXXX', 'secretvalue')


class test_Credentials__Resolver__no_routes(TestCase):

    def test__empty_route_table_returns_no_match(self):
        result = _resolver().trace(['aws', 'lambda', 'waker'])
        assert result.matched_route == ''
        assert result.matched_role  == ''

    def test__empty_command_returns_empty(self):
        result = _resolver().trace([])
        assert result.matched_route == ''
        assert result.matched_role  == ''

    def test__no_match_role_chain_is_empty(self):
        result = _resolver().trace(['aws', 's3', 'ls'])
        assert result.role_chain == []

    def test__no_match_source_creds_is_not_found(self):
        result = _resolver().trace(['aws', 's3', 'ls'])
        assert 'not found' in result.source_creds


class test_Credentials__Resolver__with_routes(TestCase):

    def setUp(self):
        self.store = _store()
        _add_role(self.store, 'default')
        _add_role(self.store, 'admin', arn='arn:aws:iam::123456789012:role/sg-admin')
        self.store.routes_set([
            {'pattern': 'aws lambda *', 'role': 'admin'},
            {'pattern': 'aws s3 *',     'role': 'default'},
        ])

    def test__matching_route_returns_correct_role(self):
        resolver = _resolver(self.store)
        result   = resolver.trace(['aws', 'lambda', 'waker', 'info'])
        assert result.matched_role  == 'admin'
        assert result.matched_route == 'aws lambda *'

    def test__matching_role_chain_contains_role(self):
        result = _resolver(self.store).trace(['aws', 'lambda', 'waker'])
        assert 'admin' in result.role_chain

    def test__assume_role_arn_is_resolved(self):
        result = _resolver(self.store).trace(['aws', 'lambda', 'waker'])
        assert result.would_assume_arn == 'arn:aws:iam::123456789012:role/sg-admin'

    def test__session_name_template_contains_role(self):
        result = _resolver(self.store).trace(['aws', 'lambda', 'waker'])
        assert 'admin' in result.session_name_tmpl
        assert '<ts>' in result.session_name_tmpl

    def test__command_path_is_preserved(self):
        path   = ['aws', 'lambda', 'waker', 'info']
        result = _resolver(self.store).trace(path)
        assert result.command_path == path

    def test__non_matching_command_returns_empty_role(self):
        result = _resolver(self.store).trace(['aws', 'ec2', 'describe'])
        assert result.matched_role == ''

    def test__no_aws_calls_made(self):                       # pure in-memory — no real boto3
        result = _resolver(self.store).trace(['aws', 'lambda', 'waker'])
        assert result is not None                            # if STS were called it would raise


class test_Credentials__Resolver__direct_creds(TestCase):

    def setUp(self):
        self.store = _store()
        _add_role(self.store, 'default')                    # direct creds — no assume_role_arn
        self.store.routes_set([
            {'pattern': 'aws s3 *', 'role': 'default'},
        ])

    def test__direct_creds_would_assume_arn_is_empty(self):
        result = _resolver(self.store).trace(['aws', 's3', 'ls'])
        assert result.would_assume_arn == ''

    def test__direct_creds_source_creds_shows_keyring(self):
        result = _resolver(self.store).trace(['aws', 's3', 'ls'])
        assert 'keyring' in result.source_creds
