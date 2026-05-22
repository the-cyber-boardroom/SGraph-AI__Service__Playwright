# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Loadout__Assembler
# Turns a workflow (or a --tools flag) into a Loadout, and resolves which registered
# actions that loadout actually grants (scope coverage via the privilege resolver) +
# the SKILL prose to inject. The model only ever sees granted actions (decision #10).
# Pure — no AWS, no boto3.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Grant      import List__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Loadout  import Schema__Tui_Api__Loadout
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Workflow import Schema__Tui_Api__Workflow
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Token            import Tui_Api__Token


class Tui_Api__Loadout__Assembler(Type_Safe):
    token : Tui_Api__Token

    def from_tools(self, spec: str) -> Schema__Tui_Api__Loadout:                  # 'sg-aws.s3:read, sg-edge.slugs:*' → Loadout
        grants = List__Tui_Api__Grant()
        for part in (spec or '').split(','):
            part = part.strip()
            if part:
                grants.append(self.token.parse(part))
        loadout = Schema__Tui_Api__Loadout()
        loadout.grants = grants
        return loadout

    def from_workflow(self, workflow: Schema__Tui_Api__Workflow) -> Schema__Tui_Api__Loadout:
        loadout = Schema__Tui_Api__Loadout()
        loadout.grants   = workflow.grants
        loadout.workflow = str(workflow.name)
        return loadout

    def granted_actions(self, loadout: Schema__Tui_Api__Loadout, registry, resolver) -> list:
        out = []                                                                  # [(slug, action)] the loadout actually grants
        for slug in registry.list_slugs():
            for action in registry.get(slug).manifest().actions:
                if resolver.grants_cover(loadout.grants, action):
                    out.append((slug, action))
        return out

    def skills_markup(self, loadout: Schema__Tui_Api__Loadout, registry, resolver) -> str:
        parts = []                                                                # SKILL-api prose for providers with ≥1 granted action
        for slug in registry.list_slugs():
            provider = registry.get(slug)
            if any(resolver.grants_cover(loadout.grants, action) for action in provider.manifest().actions):
                api_skill = provider.skills().get('api')
                if api_skill:
                    parts.append(api_skill)
        return '\n\n'.join(parts)
