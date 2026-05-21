# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Token
# The SG/Role wire form: a scope string {api}:{capability}[:{resource}] <-> a Grant.
# Also the coverage + expiry logic the resolver leans on. Pure — no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import fnmatch

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope import Schema__Tui_Api__Scope


class Tui_Api__Token(Type_Safe):

    def parse(self, token: str) -> Schema__Tui_Api__Grant:                        # 'api:cap[:resource]' -> Grant (resource keeps any extra colons)
        parts      = token.split(':', 2)
        api        = parts[0]
        capability = parts[1] if len(parts) > 1 else '*'
        resource   = parts[2] if len(parts) > 2 else '*'
        return Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api=api, capability=capability, resource=resource))

    def format(self, grant: Schema__Tui_Api__Grant) -> str:
        scope = grant.scope
        return f'{scope.api}:{scope.capability}:{scope.resource}'

    def is_expired(self, grant: Schema__Tui_Api__Grant, now: float) -> bool:
        return grant.expires_at != 0 and now > grant.expires_at

    def covers(self, grant: Schema__Tui_Api__Grant, scope: Schema__Tui_Api__Scope) -> bool:
        granted = grant.scope
        if str(granted.api) != str(scope.api):                                    # different API → no
            return False
        if str(granted.capability) != '*' and str(granted.capability) != str(scope.capability):
            return False                                                          # narrower capability → no (unless '*')
        granted_resource = str(granted.resource)
        if granted_resource == '*':                                               # whole-resource grant covers anything
            return True
        return fnmatch.fnmatch(str(scope.resource), granted_resource)             # else glob-match the action's resource
