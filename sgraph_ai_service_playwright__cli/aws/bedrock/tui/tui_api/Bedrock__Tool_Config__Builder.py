# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api: Bedrock__Tool_Config__Builder
# Maps selected TUI API actions → a Bedrock `toolConfig` (the model's tools) plus a
# name→(slug, action) routing map the engine uses to dispatch a toolUse back through
# the execution center. Bedrock tool names must match [a-zA-Z0-9_-]{1,64}; the dotted
# slug is sanitised and remembered in the map. Pure — no boto3.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Bedrock__Tool_Config__Builder(Type_Safe):

    def tool_name(self, slug: str, action: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]', '_', f'{slug}__{action}')[:64]

    def build(self, actions_by_slug: list) -> tuple:                              # [(slug, Schema__Tui_Api__Action)] → (tool_config, name_map)
        tools    = []
        name_map = {}
        for slug, action in actions_by_slug:
            name           = self.tool_name(slug, str(action.name))
            name_map[name] = (slug, str(action.name))
            tools.append({'toolSpec': {'name'       : name,
                                       'description': action.description,
                                       'inputSchema': {'json': action.input_schema}}})
        return ({'tools': tools}, name_map)
