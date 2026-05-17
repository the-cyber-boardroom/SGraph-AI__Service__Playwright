# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__Name__Resolver
# Covers: 5-tier scoring, caching, ambiguity error, not-found error,
#         exact mode, clear-winner rule.
# No mocks. Uses Lambda__AWS__Client__In_Memory as the backing client.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Name__Resolver import Lambda__Name__Resolver
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import (
    Lambda__AWS__Client__In_Memory,
    Lambda__Deployer__In_Memory,
)

_FUNCTIONS = [
    'sg-compute-vault-publish-waker',
    'sg-playwright-dev',
    'sg-playwright-baseline-dev',
    'sgraph-ai-app-send-admin-dev',
    'sgraph-ai-app-send-user-dev',
    'sp-playwright-cli-dev',
    'sp-playwright-cli-prod',
    'unrelated-function',
]


def _resolver(names: list = None) -> Lambda__Name__Resolver:
    names = names if names is not None else _FUNCTIONS
    client = Lambda__AWS__Client__In_Memory()
    for name in names:
        deployer = Lambda__Deployer__In_Memory(aws_client=client)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(name),
            folder_path = '/tmp/fake',
            handler     = 'h:h',
            role_arn    = 'arn:aws:iam::123456789012:role/r',
        )
        deployer.deploy_from_folder(req)
    resolver = Lambda__Name__Resolver(aws_client=client)
    return resolver


# ═══════════════════════════════════════════════════════════════════════════════
class TestTier1ExactMatch:

    def test_exact_match_resolved(self):
        r    = _resolver()
        name = r.resolve('sg-compute-vault-publish-waker')
        assert name == 'sg-compute-vault-publish-waker'

    def test_exact_match_with_exact_flag(self):
        r = _resolver()
        assert r.resolve('unrelated-function', exact=True) == 'unrelated-function'

    def test_exact_flag_fails_on_partial(self):
        r = _resolver()
        with pytest.raises(ValueError, match='exact'):
            r.resolve('waker', exact=True)


# ═══════════════════════════════════════════════════════════════════════════════
class TestTier3PrefixMatch:

    def test_prefix_unique_resolves(self):
        r    = _resolver()
        name = r.resolve('sg-compute')
        assert name == 'sg-compute-vault-publish-waker'

    def test_short_prefix_unique(self):
        r    = _resolver()
        name = r.resolve('unrel')
        assert name == 'unrelated-function'


# ═══════════════════════════════════════════════════════════════════════════════
class TestTier4SubstringMatch:

    def test_substring_unique_resolves(self):
        r    = _resolver()
        name = r.resolve('waker')
        assert name == 'sg-compute-vault-publish-waker'

    def test_short_substring_unique(self):
        r    = _resolver()
        name = r.resolve('vault')
        assert name == 'sg-compute-vault-publish-waker'


# ═══════════════════════════════════════════════════════════════════════════════
class TestTier5SubsequenceMatch:

    def test_subsequence_unique(self):
        r = _resolver(['only-function-here'])
        assert r.resolve('ofh') == 'only-function-here'


# ═══════════════════════════════════════════════════════════════════════════════
class TestAmbiguityError:

    def test_ambiguous_raises(self):
        r = _resolver()
        with pytest.raises(ValueError, match='Ambiguous'):
            r.resolve('sg')

    def test_ambiguous_message_lists_candidates(self):
        r = _resolver()
        try:
            r.resolve('sg')
        except ValueError as exc:
            assert 'sg-compute-vault-publish-waker' in str(exc) or 'sg-playwright' in str(exc)


# ═══════════════════════════════════════════════════════════════════════════════
class TestNotFoundError:

    def test_not_found_raises(self):
        r = _resolver()
        with pytest.raises(ValueError, match='No function matching'):
            r.resolve('xyz-completely-unknown-99999')

    def test_not_found_suggests_closest(self):
        r = _resolver()
        try:
            r.resolve('xyz-completely-unknown-99999')
        except ValueError as exc:
            assert 'Closest' in str(exc)


# ═══════════════════════════════════════════════════════════════════════════════
class TestClearWinnerRule:

    def test_single_match_auto_resolves(self):
        r = _resolver(['alpha-function', 'beta-function', 'gamma-function'])
        assert r.resolve('alpha') == 'alpha-function'


# ═══════════════════════════════════════════════════════════════════════════════
class TestCache:

    def test_cache_populated_on_first_call(self):
        r     = _resolver()
        names = r.all_function_names()
        assert len(names) == len(_FUNCTIONS)

    def test_cache_returns_same_list(self):
        r      = _resolver()
        first  = r.all_function_names()
        second = r.all_function_names()
        assert first == second

    def test_invalidate_clears_cache(self):
        r = _resolver()
        r.all_function_names()
        r.invalidate_cache()
        assert r._cache_names is None


# ═══════════════════════════════════════════════════════════════════════════════
class TestAllFunctionNames:

    def test_empty_when_no_functions(self):
        client   = Lambda__AWS__Client__In_Memory()
        resolver = Lambda__Name__Resolver(aws_client=client)
        assert resolver.all_function_names() == []
