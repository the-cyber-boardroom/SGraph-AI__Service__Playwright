# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Resolver
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name     import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config   import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS            import Keyring__Mac__OS__In_Memory
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store          import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Resolver       import Credentials__Resolver


def _store() -> Credentials__Store:
    return Credentials__Store(keyring=Keyring__Mac__OS__In_Memory())


def _cfg(name: str, region: str = 'us-east-1') -> Schema__AWS__Role__Config:
    return Schema__AWS__Role__Config(
        name            = Safe_Str__Role__Name(name),
        region          = Safe_Str__AWS__Region(region),
        assume_role_arn = Safe_Str__AWS__Role__ARN(''),
        session_name    = Safe_Str__Role__Name(f'sg-{name}'),
    )


class test_Credentials__Resolver(TestCase):

    def test_trace_with_matching_rule(self):
        store = _store()
        store.route_add('aws lambda *', 'lambda-role')
        store.role_set(_cfg('lambda-role', 'us-east-1'))
        resolver = Credentials__Resolver(store=store)
        result   = resolver.trace(['aws', 'lambda', 'list-functions'])
        assert result.matched_role == 'lambda-role'

    def test_trace_no_match_returns_empty_role(self):
        store = _store()
        store.role_set(_cfg('default', 'us-east-1'))
        resolver = Credentials__Resolver(store=store)
        result   = resolver.trace(['ec2', 'describe-instances'])
        assert result.matched_role == ''                                  # no route match

    def test_trace_no_roles_returns_empty_role(self):
        store    = _store()
        resolver = Credentials__Resolver(store=store)
        result   = resolver.trace(['aws', 'sts', 'get-caller-identity'])
        assert result.matched_role == ''

    def test_trace_first_match_wins(self):
        store = _store()
        store.route_add('aws *',        'catch-all-role')
        store.route_add('aws lambda *', 'lambda-role')
        store.role_set(_cfg('catch-all-role', 'us-east-1'))
        store.role_set(_cfg('lambda-role',    'us-east-1'))
        resolver = Credentials__Resolver(store=store)
        result   = resolver.trace(['aws', 'lambda', 'invoke'])
        assert result.matched_role == 'catch-all-role'                    # first match wins

    def test_trace_wildcard_star_matches_anything(self):
        store = _store()
        store.route_add('*', 'super-default')
        store.role_set(_cfg('super-default', 'us-east-1'))
        resolver = Credentials__Resolver(store=store)
        result   = resolver.trace(['anything', 'at', 'all'])
        assert result.matched_role == 'super-default'
