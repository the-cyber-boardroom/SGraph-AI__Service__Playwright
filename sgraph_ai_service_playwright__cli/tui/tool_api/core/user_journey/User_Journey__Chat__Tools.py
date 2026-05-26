# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: User_Journey__Chat__Tools
# The bridge the chat cockpit uses: a user-journey workflow → the neutral chat tools
# (+ name_map) the agentic loop dispatches. Composes the existing pieces — registry,
# loadout assembler, Chat__Tool__Builder — so the LLM only ever sees the actions the
# chosen workflow grants (monitor < operate < load).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder                          import Chat__Tool__Builder
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Tui_Api__Provider import User_Journey__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler              import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                        import Tui_Api__Registry


class User_Journey__Chat__Tools(Type_Safe):

    def registry(self, conductor=None) -> Tui_Api__Registry:
        provider = User_Journey__Tui_Api__Provider()
        if conductor is not None:
            provider.conductor = conductor
        return Tui_Api__Registry().register(provider)

    def build_for_workflow(self, workflow, registry, resolver) -> tuple:           # workflow → (List__Chat__Tool, name_map)
        assembler = Tui_Api__Loadout__Assembler()
        loadout   = assembler.from_workflow(workflow)
        granted   = assembler.granted_actions(loadout, registry, resolver)
        return Chat__Tool__Builder().build(granted)
