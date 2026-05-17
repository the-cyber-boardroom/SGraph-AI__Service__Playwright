# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Model__Resolver
# Translates user-facing model aliases (e.g. "opus-4.7", "haiku-4.5") to the
# canonical Bedrock model ID or inference-profile ARN for the active region.
#
# Single source of truth for model-ID complexity.  No other class (CLI verbs,
# service clients, tests) is allowed to hard-code Bedrock model IDs.
#
# Alias table: Bedrock__Model__Aliases.BEDROCK_MODEL_ALIASES (plain Python
# dict; no YAML / JSON / disk I/O). Tests subclass and override aliases().
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import Optional

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Provider import Enum__Bedrock__Provider
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id import Safe_Str__Bedrock__Model_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Aliases       import BEDROCK_MODEL_ALIASES

# ── Provider keyword → Enum__Bedrock__Provider ────────────────────────────────

_PROVIDER_MAP = {
    'claude'  : Enum__Bedrock__Provider.CLAUDE ,
    'nova'    : Enum__Bedrock__Provider.NOVA   ,
    'llama'   : Enum__Bedrock__Provider.LLAMA  ,
    'openai'  : Enum__Bedrock__Provider.OPENAI ,
}


class Bedrock__Model__Resolver(Type_Safe):

    # ── Alias loading ─────────────────────────────────────────────────────────

    def aliases(self) -> dict:                                                      # Override in tests for controlled fixtures
        return BEDROCK_MODEL_ALIASES

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve(self, provider: str, alias: str = 'default', region: str = '') -> str:
        """Return the canonical model ID for provider+alias+region."""           # inline
        table = self.aliases()
        provider_key = provider.lower()
        provider_section = table.get(provider_key, {})
        if not provider_section:
            raise ValueError(f'Unknown provider: {provider!r}')

        # Check region+provider specific override first (covers 'default' alias too).
        # Override table is provider-scoped: region_overrides[region][provider][alias]
        region_overrides = table.get('region_overrides', {})
        if region:
            override = region_overrides.get(region, {}).get(provider_key, {}).get(alias)
            if override:
                return override

        # Fall back to provider section — raise for unknown non-default alias
        if alias != 'default' and alias not in provider_section:
            raise ValueError(f'Unknown alias {alias!r} for provider {provider!r}')
        model_id = provider_section.get(alias) or provider_section.get('default', '')
        if not model_id:
            raise ValueError(f'Unknown alias {alias!r} for provider {provider!r}')
        return model_id

    def resolve_safe(self, provider: str, alias: str = 'default', region: str = '') -> Safe_Str__Bedrock__Model_Id:
        raw = self.resolve(provider, alias, region)                               # wraps resolve in the primitive type
        return Safe_Str__Bedrock__Model_Id(raw)

    def provider_enum(self, provider: str) -> Enum__Bedrock__Provider:            # Map provider keyword to enum
        key = provider.lower()
        return _PROVIDER_MAP.get(key, Enum__Bedrock__Provider.OTHER)

    def list_aliases(self, provider: str) -> list:                                # Returns all known aliases for a provider (excluding 'default')
        table   = self.aliases()
        section = table.get(provider.lower(), {})
        return [k for k in section if k != 'default']
