# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Model__Resolver
# All tests use a Resolver subclass that loads aliases from a controlled dict.
# No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Provider          import Enum__Bedrock__Provider
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id import Safe_Str__Bedrock__Model_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver       import Bedrock__Model__Resolver

# ── Controlled alias table (no disk I/O) ─────────────────────────────────────

_FAKE_ALIASES = {
    'claude': {
        'default'   : 'anthropic.claude-3-5-haiku-20241022-v1:0',
        'haiku-4.5' : 'anthropic.claude-haiku-4-5:0'            ,
        'sonnet-4.6': 'anthropic.claude-sonnet-4-6:0'           ,
        'opus-4.7'  : 'us.anthropic.claude-opus-4-7:0'          ,
    },
    'nova': {
        'default': 'amazon.nova-lite-v1:0',
        'lite'   : 'amazon.nova-lite-v1:0',
        'pro'    : 'amazon.nova-pro-v1:0' ,
    },
    'llama': {
        'default': 'meta.llama3-8b-instruct-v1:0',
        '3.1'    : 'meta.llama3-1-8b-instruct-v1:0',
    },
    'region_overrides': {
        'eu-west-1': {
            'opus-4.7': 'eu.anthropic.claude-opus-4-7:0',
        },
    },
}


class _Fake__Resolver(Bedrock__Model__Resolver):                                 # Skips YAML I/O — injects the controlled alias table
    def aliases(self) -> dict:
        return _FAKE_ALIASES


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Bedrock__Model__Resolver(TestCase):

    def setUp(self):
        self.resolver = _Fake__Resolver()

    # ── resolve ───────────────────────────────────────────────────────────────

    def test__resolve__default_claude_returns_haiku(self):
        mid = self.resolver.resolve('claude', 'default')
        assert mid == 'anthropic.claude-3-5-haiku-20241022-v1:0'

    def test__resolve__claude_haiku_45_alias(self):
        mid = self.resolver.resolve('claude', 'haiku-4.5')
        assert mid == 'anthropic.claude-haiku-4-5:0'

    def test__resolve__claude_sonnet_46_alias(self):
        mid = self.resolver.resolve('claude', 'sonnet-4.6')
        assert mid == 'anthropic.claude-sonnet-4-6:0'

    def test__resolve__nova_default(self):
        mid = self.resolver.resolve('nova', 'default')
        assert mid == 'amazon.nova-lite-v1:0'

    def test__resolve__nova_pro(self):
        mid = self.resolver.resolve('nova', 'pro')
        assert mid == 'amazon.nova-pro-v1:0'

    def test__resolve__llama_3_1(self):
        mid = self.resolver.resolve('llama', '3.1')
        assert mid == 'meta.llama3-1-8b-instruct-v1:0'

    def test__resolve__unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            self.resolver.resolve('deepseek', 'default')

    def test__resolve__unknown_alias_raises(self):
        with self.assertRaises(ValueError):
            self.resolver.resolve('claude', 'does-not-exist')

    # ── region overrides ──────────────────────────────────────────────────────

    def test__resolve__opus_47_uses_region_override_eu(self):
        mid = self.resolver.resolve('claude', 'opus-4.7', region='eu-west-1')
        assert mid == 'eu.anthropic.claude-opus-4-7:0'

    def test__resolve__opus_47_no_override_returns_default(self):
        mid = self.resolver.resolve('claude', 'opus-4.7', region='ap-southeast-1')
        assert mid == 'us.anthropic.claude-opus-4-7:0'                          # default from alias table

    # ── resolve_safe ──────────────────────────────────────────────────────────

    def test__resolve_safe__returns_safe_str_type(self):
        safe = self.resolver.resolve_safe('nova', 'lite')
        assert isinstance(safe, Safe_Str__Bedrock__Model_Id)

    def test__resolve_safe__value_correct(self):
        safe = self.resolver.resolve_safe('nova', 'lite')
        assert str(safe) == 'amazon.nova-lite-v1:0'

    # ── provider_enum ─────────────────────────────────────────────────────────

    def test__provider_enum__claude(self):
        assert self.resolver.provider_enum('claude') == Enum__Bedrock__Provider.CLAUDE

    def test__provider_enum__nova(self):
        assert self.resolver.provider_enum('nova') == Enum__Bedrock__Provider.NOVA

    def test__provider_enum__llama(self):
        assert self.resolver.provider_enum('llama') == Enum__Bedrock__Provider.LLAMA

    def test__provider_enum__unknown_maps_to_other(self):
        assert self.resolver.provider_enum('unknown') == Enum__Bedrock__Provider.OTHER

    # ── list_aliases ──────────────────────────────────────────────────────────

    def test__list_aliases__claude(self):
        aliases = self.resolver.list_aliases('claude')
        assert 'haiku-4.5' in aliases
        assert 'default'   not in aliases                                        # default excluded

    def test__list_aliases__nova(self):
        aliases = self.resolver.list_aliases('nova')
        assert 'lite' in aliases
        assert 'pro'  in aliases
