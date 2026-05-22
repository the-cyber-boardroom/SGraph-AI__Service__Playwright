# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Chat__Tool__Builder (neutral)
# Granted TUI API actions → neutral Schema__Chat__Tool specs + a name→(slug,action)
# routing map. Names are sanitised to [a-zA-Z0-9_-]{1,64} (valid for Bedrock AND
# OpenAI), so backends wrap only the SHAPE, never the names. Pure — no backend deps.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Tool   import List__Chat__Tool
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool import Schema__Chat__Tool


class Chat__Tool__Builder(Type_Safe):

    def tool_name(self, slug: str, action: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]', '_', f'{slug}__{action}')[:64]

    def build(self, granted_actions: list) -> tuple:                              # [(slug, action)] → (List__Chat__Tool, name_map)
        tools    = List__Chat__Tool()
        name_map = {}
        for slug, action in granted_actions:
            name           = self.tool_name(slug, str(action.name))
            name_map[name] = (slug, str(action.name))
            tools.append(Schema__Chat__Tool(name=name, description=action.description, input_schema=action.input_schema))
        return (tools, name_map)
