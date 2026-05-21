# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Registry
# The single source of truth the CLI, the chat, the explorer, and pytest all read.
# v1 uses EXPLICIT per-area registration (no command-tree walking exists today).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.service.List__Tui_Api__Provider import List__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider       import Tui_Api__Provider


class Tui_Api__Registry(Type_Safe):
    providers : List__Tui_Api__Provider

    def register(self, provider: Tui_Api__Provider) -> 'Tui_Api__Registry':
        self.providers.append(provider)
        return self

    def get(self, slug: str) -> Tui_Api__Provider:
        for provider in self.providers:
            if str(provider.manifest().slug) == slug:
                return provider
        return None

    def list_slugs(self) -> list:
        return sorted(str(provider.manifest().slug) for provider in self.providers)
