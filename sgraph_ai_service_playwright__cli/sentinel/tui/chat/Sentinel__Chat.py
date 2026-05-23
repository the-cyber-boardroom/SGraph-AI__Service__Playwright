# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Chat
# Assembles the "talk to SG/Sentinel" chat: the read-only Sentinel__Tui_Api__Provider
# (tools) + the shared Chat__Engine + a Bedrock **Nova** backend (default model
# 'micro' — cheapest Nova), driven through the gated Tui_Api__Execution_Center. The
# LLM can only call the provider's read actions, so answers are grounded in live
# state and nothing is mutated. Inject a scripted backend for tests (no AWS, no LLM).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source            import Sentinel__TUI__Source
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.Sentinel__Tui_Api__Provider     import Sentinel__Tui_Api__Provider, SLUG
from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend                       import Chat__Backend
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Engine                        import Chat__Engine
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder                 import Chat__Tool__Builder
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center       import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry               import Tui_Api__Registry

_SYSTEM = ('You are the SG/Sentinel assistant — a read-only edge-guard operator helper. '
           'Answer questions about rules, logged requests, blocks, deployment status, the engine code, '
           'and traffic runs by CALLING THE TOOLS to read live state. Never guess or fabricate verdicts, '
           'rule ids, IPs or counts — if a tool returns nothing, say so. You cannot change anything.\n\n')


class Sentinel__Chat(Type_Safe):
    source  : Sentinel__TUI__Source
    backend : Chat__Backend = None                                                   # None → live Bedrock Nova
    model   : Safe_Str      = Safe_Str('micro')                                       # cheapest Nova (amazon.nova-micro-v1:0)

    def _backend(self) -> Chat__Backend:
        if self.backend is not None:
            return self.backend
        from sgraph_ai_service_playwright__cli.aws.bedrock.chat.Chat__Backend__Bedrock      import Chat__Backend__Bedrock
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__AWS_Source import Bedrock__Chat__AWS_Source
        return Chat__Backend__Bedrock(source=Bedrock__Chat__AWS_Source(), region='us-east-1')

    def provider(self) -> Sentinel__Tui_Api__Provider:
        return Sentinel__Tui_Api__Provider(source=self.source)

    def tools_and_map(self, provider):
        granted = [(SLUG, action) for action in provider.manifest().actions]
        return Chat__Tool__Builder().build(granted)

    def new_session(self):
        provider = self.provider()
        system   = _SYSTEM + provider.skills().get('api', '')
        return Chat__Engine(backend=self._backend()).new_session(model_id=str(self.model), system=system, budget_usd=0.50)

    def ask(self, session, text):                                                    # one turn against a session → Schema__Chat__Turn
        provider        = self.provider()
        registry        = Tui_Api__Registry().register(provider)
        center          = Tui_Api__Execution_Center(registry=registry)               # READ_ONLY actions run ungated
        tools, name_map = self.tools_and_map(provider)
        engine          = Chat__Engine(backend=self._backend())
        return engine.send_turn_agentic(session, text, center, tools, name_map)
