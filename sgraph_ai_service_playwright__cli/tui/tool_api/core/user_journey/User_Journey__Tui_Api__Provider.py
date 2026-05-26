# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: User_Journey__Tui_Api__Provider
# The "talk to the tools" seam for browser user-journey suites. A thin, honest
# mapping of conductor operations to tool-API actions — no gating of its own; the
# execution center gates WRITE/DESTRUCTIVE (start/stop/scale) via dry-run + mutation
# gate + audit. dispatch() routes through a Conductor__Client (HTTP to the on-box
# conductor). manifest() is pure. The same provider backs the cockpit buttons, the
# chat cockpit's LLM tools, and the CLI passthrough verbs.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.schemas.Schema__UJ__Params__Scale         import Schema__UJ__Params__Scale
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.schemas.Schema__UJ__Params__Suite_Ref     import Schema__UJ__Params__Suite_Ref
from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.schemas.Schema__UJ__Params__Suite_Run_Ref import Schema__UJ__Params__Suite_Run_Ref
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier        import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action     import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier       import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action   import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result   import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope    import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider        import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder  import Tui_Api__Schema__Builder

from sg_compute_specs.user_journey.core.clients.Conductor__Client import Conductor__Client


API_SLUG = 'browser.user-journey'

_TIERS = {'uj.status': Enum__Tui_Api__Tier.READ_ONLY,   'uj.flows': Enum__Tui_Api__Tier.READ_ONLY,
          'uj.start' : Enum__Tui_Api__Tier.WRITE,        'uj.stop' : Enum__Tui_Api__Tier.WRITE,
          'uj.scale' : Enum__Tui_Api__Tier.DESTRUCTIVE}                            # scale launches containers → cost; gated hardest

_CAPABILITIES = {'uj.status': 'read', 'uj.flows': 'read',
                 'uj.start' : 'write', 'uj.stop': 'write', 'uj.scale': 'scale'}


class User_Journey__Tui_Api__Provider(Tui_Api__Provider):
    conductor : Conductor__Client                                                 # HTTP to the on-box conductor
    builder   : Tui_Api__Schema__Builder

    def manifest(self) -> Schema__Tui_Api__Manifest:
        actions = List__Tui_Api__Action()
        actions.append(self._action('uj.status', 'Live status of a running suite.',                 Schema__UJ__Params__Suite_Run_Ref))
        actions.append(self._action('uj.flows',  'Captured network flows for a suite run.',         Schema__UJ__Params__Suite_Run_Ref))
        actions.append(self._action('uj.start',  'Start a vault-stored suite by id.',               Schema__UJ__Params__Suite_Ref))
        actions.append(self._action('uj.stop',   'Stop a running suite.',                           Schema__UJ__Params__Suite_Run_Ref))
        actions.append(self._action('uj.scale',  'Rescale a running suite (cost-bearing load knob).', Schema__UJ__Params__Scale))

        tiers = List__Tui_Api__Tier()
        for tier in (Enum__Tui_Api__Tier.READ_ONLY, Enum__Tui_Api__Tier.WRITE, Enum__Tui_Api__Tier.DESTRUCTIVE):
            tiers.append(tier)

        return Schema__Tui_Api__Manifest(slug=API_SLUG, tool='browser', name='Browser User-Journey',
                                         version='0.1.0',
                                         description='Run and monitor browser user-journey suites on the conductor.',
                                         tiers=tiers, actions=actions)

    def _action(self, name: str, description: str, params_cls) -> Schema__Tui_Api__Action:
        tier = _TIERS[name]
        return Schema__Tui_Api__Action(name=name, description=description, tier=tier,
                                       scope=Schema__Tui_Api__Scope(api=API_SLUG, capability=_CAPABILITIES[name]),
                                       input_schema=self.builder.input_schema(params_cls),
                                       supports_dry_run=(tier != Enum__Tui_Api__Tier.READ_ONLY))

    def dry_run(self, action: str, params: dict) -> dict:
        if action == 'uj.start':
            return {'suite_id': params.get('suite_id'), 'would_start': True}
        if action == 'uj.stop':
            return {'suite_run_id': params.get('suite_run_id'), 'would_stop': True}
        if action == 'uj.scale':
            return {'suite_run_id'      : params.get('suite_run_id'),
                    'target_count'      : params.get('count'),
                    'target_concurrency': params.get('concurrency')}
        return {}

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        try:
            if   action == 'uj.status':
                ref  = Schema__UJ__Params__Suite_Run_Ref(**params)
                data = self.conductor.get_suite(str(ref.suite_run_id)).json()
            elif action == 'uj.flows':
                ref  = Schema__UJ__Params__Suite_Run_Ref(**params)
                data = {'flows': self.conductor.get_flows(str(ref.suite_run_id))}
            elif action == 'uj.start':
                ref  = Schema__UJ__Params__Suite_Ref(**params)
                data = self.conductor.start_suite_id(str(ref.suite_id)).json()
            elif action == 'uj.stop':
                ref  = Schema__UJ__Params__Suite_Run_Ref(**params)
                data = self.conductor.stop_suite(str(ref.suite_run_id)).json()
            elif action == 'uj.scale':
                ref  = Schema__UJ__Params__Scale(**params)
                data = self.conductor.scale_suite(str(ref.suite_run_id), int(ref.count), int(ref.concurrency)).json()
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except Exception as exc:
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})
