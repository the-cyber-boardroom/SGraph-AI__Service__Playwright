# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Skills
# Refs to the three SKILL audiences (human / api / driver) — relative filenames
# under the provider's skills/ dir. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Tui_Api__Skills(Type_Safe):
    human  : str = 'SKILL-human.md'
    api    : str = 'SKILL-api.md'
    driver : str = 'SKILL-driver.md'
