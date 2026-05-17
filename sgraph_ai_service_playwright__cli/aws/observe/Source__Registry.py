# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — Source__Registry
# Discovers and returns available source adapters by name.
# Adapters are registered at construction time; callers inject adapters rather
# than the registry constructing them (keeps it testable without AWS creds).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract import Source__Contract


class Source__Registry(Type_Safe):
    _adapters : dict                                                    # name → Source__Contract

    def register(self, name: str, adapter: Source__Contract) -> None:
        self._adapters[name] = adapter

    def list_sources(self) -> list:                                     # list[dict] — one entry per adapter
        result = []
        for name, adapter in self._adapters.items():
            result.append({'name': name, 'adapter': adapter})
        return result

    def get_source(self, name: str):                                    # → Source__Contract | None
        return self._adapters.get(name)

    def source_names(self) -> list:
        return list(self._adapters.keys())
