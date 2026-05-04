# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Skill — GET /admin/skills/{name} response (v0.1.29)
#
# Raw markdown SKILL document for a given audience. `name` is one of human /
# browser / agent. Returning markdown in a JSON envelope (rather than text/plain)
# keeps the route behaviour consistent with every other admin endpoint; agents
# can still extract `content` and render it locally.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Markdown                import Safe_Str__Markdown
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                    import Safe_Str__Text


class Schema__Agentic__Skill(Type_Safe):
    name    : Safe_Str__Text                                                        # 'human' / 'browser' / 'agent'
    content : Safe_Str__Markdown                                                    # Verbatim markdown body of skill__{name}.md
