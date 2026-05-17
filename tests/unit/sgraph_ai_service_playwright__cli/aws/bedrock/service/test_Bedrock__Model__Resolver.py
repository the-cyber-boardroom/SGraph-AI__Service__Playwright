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
        'default'    : 'anthropic.claude-3-5-haiku-20241022-v1:0',
        'haiku-4.5'  : 'anthropic.claude-haiku-4-5:0'            ,
        'sonnet-4.6' : 'anthropic.claude-sonnet-4-6'             ,   # no :0 suffix
        'sonnet-3.5' : 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        'opus-4.7'   : 'us.anthropic.claude-opus-4-7:0'          ,
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
            'claude': {
                'default'    : 'eu.anthropic.claude-3-5-haiku-20241022-v1:0',
                'haiku-4.5'  : 'eu.anthropic.claude-haiku-4-5:0'            ,
                'sonnet-3.5' : 'eu.anthropic.claude-3-5-sonnet-20241022-v2:0',
                'opus-4.7'   : 'eu.anthropic.claude-opus-4-7:0'             ,
            },
        },
        'eu-west-2': {
            'claude': {
                'default'  : 'eu.anthropic.claude-3-5-haiku-20241022-v1:0',
                'opus-4.7' : 'eu.anthropic.claude-opus-4-7:0'             ,
            },
        },
        'ap-northeast-1': {
            'claude': {
                'default'  : 'apac.anthropic.claude-3-5-haiku-20241022-v1:0',
                'opus-4.7' : 'apac.anthropic.claude-opus-4-7:0'              ,
            },
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
        assert mid == 'anthropic.claude-sonnet-4-6'                              # no :0 suffix

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

    def test__resolve__default_claude_uses_eu_override(self):
        mid = self.resolver.resolve('claude', 'default', region='eu-west-1')
        assert mid == 'eu.anthropic.claude-3-5-haiku-20241022-v1:0'

    def test__resolve__default_claude_uses_eu_override_west2(self):
        mid = self.resolver.resolve('claude', 'default', region='eu-west-2')
        assert mid == 'eu.anthropic.claude-3-5-haiku-20241022-v1:0'

    def test__resolve__default_claude_bare_in_us_east_1(self):
        mid = self.resolver.resolve('claude', 'default', region='us-east-1')
        assert mid == 'anthropic.claude-3-5-haiku-20241022-v1:0'                # no prefix in us-east-1

    def test__resolve__default_claude_bare_with_no_region(self):
        mid = self.resolver.resolve('claude', 'default')
        assert mid == 'anthropic.claude-3-5-haiku-20241022-v1:0'                # no region = no override

    def test__resolve__haiku_45_eu_override(self):
        mid = self.resolver.resolve('claude', 'haiku-4.5', region='eu-west-1')
        assert mid == 'eu.anthropic.claude-haiku-4-5:0'

    def test__resolve__sonnet_35_eu_override(self):
        mid = self.resolver.resolve('claude', 'sonnet-3.5', region='eu-west-1')
        assert mid == 'eu.anthropic.claude-3-5-sonnet-20241022-v2:0'

    def test__resolve__default_claude_uses_apac_override(self):
        mid = self.resolver.resolve('claude', 'default', region='ap-northeast-1')
        assert mid == 'apac.anthropic.claude-3-5-haiku-20241022-v1:0'

    def test__resolve__nova_default_no_region_override(self):
        mid = self.resolver.resolve('nova', 'default', region='eu-west-1')
        assert mid == 'amazon.nova-lite-v1:0'                                   # no EU override for nova

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


# ─────────────────────────────────────────────────────────────────────────────
# Real-table tests — exercise the actual BEDROCK_MODEL_ALIASES Python dict
# that the Fake__Resolver bypasses. Catches drift between the runtime table
# and the resolver's expectations (this is what caught the original
# yaml-path off-by-two before it became a yaml-import dependency story).
# ─────────────────────────────────────────────────────────────────────────────

class test_Bedrock__Model__Resolver__real_table(TestCase):

    def setUp(self):
        self.resolver = Bedrock__Model__Resolver()                                 # NO override — uses the actual BEDROCK_MODEL_ALIASES dict

    def test__aliases_is_importable_without_yaml(self):                            # ensure no `import yaml` lurks
        from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Aliases import BEDROCK_MODEL_ALIASES
        assert isinstance(BEDROCK_MODEL_ALIASES, dict)
        assert BEDROCK_MODEL_ALIASES                                                # non-empty

    def test__aliases_contains_all_providers(self):
        table = self.resolver.aliases()
        assert table                                                                # non-empty
        for provider in ('claude', 'nova', 'llama'):
            assert provider in table, f'{provider!r} missing from alias table'
            assert table[provider], f'{provider!r} section is empty'

    def test__resolve_nova_default_from_real_table(self):                          # the exact path that broke for the user 2026-05-17
        mid = self.resolver.resolve('nova', 'default')
        assert mid.startswith('amazon.nova-')

    def test__resolve_claude_default_from_real_table(self):
        mid = self.resolver.resolve('claude', 'default')
        assert mid.startswith('anthropic.claude-')

    def test__resolve_claude_sonnet_46_has_no_colon_zero(self):                    # regression: was anthropic.claude-sonnet-4-6:0
        mid = self.resolver.resolve('claude', 'sonnet-4.6')
        assert not mid.endswith(':0'), f'sonnet-4.6 must not carry :0 suffix; got {mid!r}'

    def test__resolve_claude_default_eu_uses_inference_profile(self):             # the user-reported trap: eu-west-2 + bare ID fails
        mid = self.resolver.resolve('claude', 'default', region='eu-west-2')
        assert mid.startswith('eu.'), f'claude default in eu-west-2 must use eu. prefix; got {mid!r}'

    def test__resolve_claude_opus_46_in_real_table(self):
        mid = self.resolver.resolve('claude', 'opus-4.6')
        assert mid == 'anthropic.claude-opus-4-6-v1'

    def test__resolve_llama_default_from_real_table(self):
        mid = self.resolver.resolve('llama', 'default')
        assert mid.startswith('meta.llama')
