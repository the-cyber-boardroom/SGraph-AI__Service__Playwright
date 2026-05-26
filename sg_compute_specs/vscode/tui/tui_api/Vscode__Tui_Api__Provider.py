# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui/tui_api: Vscode__Tui_Api__Provider
# The vscode stacks surface as a TUI API — driveable by humans, pytest, the
# explorer, and the Bedrock chat. It owns NO logic: every action delegates to the
# injected Vscode__TUI__Data_Source — the SAME Vscode__Service the `sg vscode` CLI
# uses (separation guide). Reads are READ_ONLY; delete is CRUD and the execution
# center gates it (confirm/env). state() drives preconditions via can_act.
# Mirrors SG_Edge__Tui_Api__Provider.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op         import Enum__Tui_Api__Cond_Op
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier            import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action         import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Precondition   import List__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier           import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action       import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest     import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Precondition import Schema__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result       import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope        import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Skills       import Schema__Tui_Api__Skills
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider             import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder      import Tui_Api__Schema__Builder

from sg_compute_specs.vscode.tui.source.Vscode__TUI__Data_Source                          import Vscode__TUI__Data_Source
from sg_compute_specs.vscode.tui.tui_api.schemas.Schema__Vscode__Tui_Api__Params__Stack    import Schema__Vscode__Tui_Api__Params__Stack

SLUG    = 'vscode'
TOOL    = 'vscode'
NO_ARGS = {'type': 'object', 'properties': {}}

READ_ONLY = Enum__Tui_Api__Tier.READ_ONLY
CRUD      = Enum__Tui_Api__Tier.CRUD


def _scope(capability: str) -> Schema__Tui_Api__Scope:
    return Schema__Tui_Api__Scope(api=SLUG, capability=capability)


def _can_act_precondition() -> List__Tui_Api__Precondition:
    out = List__Tui_Api__Precondition()
    out.append(Schema__Tui_Api__Precondition(state_path='can_act', op=Enum__Tui_Api__Cond_Op.EQ, value='True',
                                             note='mutations require the data source to be actionable'))
    return out


class Vscode__Tui_Api__Provider(Tui_Api__Provider):
    source  : Vscode__TUI__Data_Source
    builder : Tui_Api__Schema__Builder

    def manifest(self) -> Schema__Tui_Api__Manifest:
        stack_schema = self.builder.input_schema(Schema__Vscode__Tui_Api__Params__Stack)
        read         = _scope('read')
        write        = _scope('write')

        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='status', tier=READ_ONLY, scope=read,
                                               description='Snapshot of vscode stacks in the region (count + per-stack state/url).',
                                               input_schema=NO_ARGS))
        actions.append(Schema__Tui_Api__Action(name='list', tier=READ_ONLY, scope=read,
                                               description='List vscode stacks with state, distribution, ingress, editor URL.',
                                               input_schema=NO_ARGS))
        actions.append(Schema__Tui_Api__Action(name='delete', tier=CRUD, scope=write, supports_dry_run=True,
                                               description='Terminate a vscode stack (EC2 instance + its security group).',
                                               input_schema=stack_schema, preconditions=_can_act_precondition()))

        tiers = List__Tui_Api__Tier()
        for tier in (READ_ONLY, CRUD):
            tiers.append(tier)

        return Schema__Tui_Api__Manifest(slug=SLUG, tool=TOOL, name='VS Code stacks', version='0.1.0',
                                        description='Operate vscode EC2 stacks: read state + delete.',
                                        tiers=tiers, actions=actions, skills=Schema__Tui_Api__Skills())

    def state(self) -> dict:
        snapshot = self.source.snapshot()
        return {'can_act'    : self.source.can_act(),
                'region'     : snapshot.region,
                'stack_count': snapshot.total}

    def dry_run(self, action: str, params: dict) -> dict:
        stack = (params or {}).get('stack_name', '')
        return {'delete': {'terminates': f'{stack} (EC2 instance + security group)'}}.get(action, {})

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        params = params or {}
        try:
            if   action == 'status':
                data = self.source.snapshot().json()
            elif action == 'list':
                data = {'stacks': [s.json() for s in self.source.snapshot().stacks]}
            elif action == 'delete':
                stack = self._stack_name(params)
                data  = {'stack_name': stack, 'deleted': bool(self.source.delete(stack))}
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except ValueError as exc:
            return Schema__Tui_Api__Result(ok=False, error=str(exc))
        except Exception as exc:
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})

    def _stack_name(self, params: dict) -> str:
        stack = str(params.get('stack_name', '')).strip()
        if not stack:
            raise ValueError('stack_name is required')
        return stack
