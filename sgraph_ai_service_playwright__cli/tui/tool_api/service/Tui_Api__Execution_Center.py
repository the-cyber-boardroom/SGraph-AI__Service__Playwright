# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Execution_Center
# Mediates EVERY dispatch: precondition/sequencing → param validation → SG/Role gate
# → privilege pre-flight → preview/dry-run → mutation gate (env or confirm) → dispatch
# → audit. Pure + headless: confirmation is a caller-supplied callback; the mutation
# gate reuses the existing `..._ALLOW_MUTATIONS` convention (the CLI wires the Typer
# decorator / confirm_or_abort on top). The security boundary is still AWS IAM — this
# is the controlled, auditable funnel in front of it.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Exec_Mode        import Enum__Tui_Api__Exec_Mode
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier             import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Call            import List__Tui_Api__Call
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Call          import Schema__Tui_Api__Call
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result        import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Param__Sanitiser      import Tui_Api__Param__Sanitiser
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Precondition__Check   import Tui_Api__Precondition__Check
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver   import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry              import Tui_Api__Registry

_MUTATING_TIERS = (Enum__Tui_Api__Tier.WRITE, Enum__Tui_Api__Tier.CRUD, Enum__Tui_Api__Tier.DESTRUCTIVE)


class Tui_Api__Execution_Center(Type_Safe):
    mode         : Enum__Tui_Api__Exec_Mode = Enum__Tui_Api__Exec_Mode.AUTO
    registry     : Tui_Api__Registry
    resolver     : Tui_Api__Privilege__Resolver
    checker      : Tui_Api__Precondition__Check
    sanitiser    : Tui_Api__Param__Sanitiser
    mutation_env : str = 'SG_TUI_API__ALLOW_MUTATIONS'
    identity     : str = 'local'
    log          : List__Tui_Api__Call

    def execute(self, slug: str, action_name: str, params: dict,
                grants=None, on_confirm=None) -> Schema__Tui_Api__Result:
        started  = time.time()
        provider = self.registry.get(slug)
        if provider is None:
            return Schema__Tui_Api__Result(ok=False, error=f'no such API: {slug}')
        action = provider.action(action_name)
        if action is None:
            return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action_name}')

        ok, note = self.checker.evaluate(action.preconditions, provider.state())  # 1. sequencing
        if not ok:
            return self._audit(action, params, started, Schema__Tui_Api__Result(ok=False, error=f'unavailable: {note}'))

        error = self.validate_params(action.input_schema, params)                 # 2. param validation
        if error:
            return self._audit(action, params, started, Schema__Tui_Api__Result(ok=False, error=f'invalid params: {error}'))

        if grants is not None and not self.resolver.grants_cover(grants, action):  # 3. SG/Role gate
            return self._audit(action, params, started, Schema__Tui_Api__Result(
                ok=False, error=f'not granted: needs {action.scope.api}:{action.scope.capability}'))

        for privilege in action.privileges:                                       # 4. backing-privilege pre-flight
            miss = self.resolver.missing(privilege)
            if miss:
                return self._audit(action, params, started, Schema__Tui_Api__Result(ok=False, error=f'privilege missing: {miss}'))

        mutating = action.tier in _MUTATING_TIERS
        preview  = self._preview(provider, action, action_name, params)

        if self.mode == Enum__Tui_Api__Exec_Mode.DRY_RUN:                         # 5. dry-run → never dispatch
            return self._audit(action, params, started, Schema__Tui_Api__Result(ok=True, dry_run=True, preview=preview))

        if mutating:                                                              # 6. mutation gate (env OR confirm)
            allowed   = os.environ.get(self.mutation_env) == '1'
            confirmed = None
            if on_confirm is not None and not allowed:
                confirmed = bool(on_confirm(action, params, preview))
            if not allowed and not confirmed:
                message = 'not confirmed' if confirmed is False else f'mutation gate: set {self.mutation_env}=1 or confirm'
                return self._audit(action, params, started,
                                  Schema__Tui_Api__Result(ok=False, dry_run=True, preview=preview, error=message))

        result = provider.dispatch(action_name, params)                           # 7. dispatch
        return self._audit(action, params, started, result)                       # 8. audit

    def available_actions(self, slug: str, grants=None) -> list:                  # discovery: only currently-AVAILABLE actions
        provider = self.registry.get(slug)
        if provider is None:
            return []
        state = provider.state()
        out   = []
        for action in provider.manifest().actions:
            ok, _ = self.checker.evaluate(action.preconditions, state)
            if not ok:
                continue
            if grants is not None and not self.resolver.grants_cover(grants, action):
                continue
            out.append(action)
        return out

    def validate_params(self, input_schema: dict, params: dict) -> str:           # minimal JSON-Schema check (required + primitive types)
        if not isinstance(input_schema, dict):
            return ''
        for key in input_schema.get('required', []):
            if key not in (params or {}):
                return f'missing required: {key}'
        properties = input_schema.get('properties', {})
        for key, value in (params or {}).items():
            json_type = (properties.get(key) or {}).get('type')
            if   json_type == 'string'  and not isinstance(value, str):                       return f'{key} must be a string'
            elif json_type == 'integer' and (not isinstance(value, int) or isinstance(value, bool)): return f'{key} must be an integer'
            elif json_type == 'boolean' and not isinstance(value, bool):                      return f'{key} must be a boolean'
            elif json_type == 'number'  and (not isinstance(value, (int, float)) or isinstance(value, bool)): return f'{key} must be a number'
        return ''

    def _preview(self, provider, action, action_name: str, params: dict) -> dict:
        if not action.supports_dry_run:
            return {}
        try:
            return provider.dry_run(action_name, params)
        except Exception:
            return {}

    def _audit(self, action, params: dict, started: float, result: Schema__Tui_Api__Result) -> Schema__Tui_Api__Result:
        self.log.append(Schema__Tui_Api__Call(action_ref  = str(action.name),
                                              params      = self.sanitiser.mask(params),
                                              scope_used  = action.scope,
                                              mode        = self.mode,
                                              result_ok   = result.ok,
                                              error       = result.error,
                                              duration_ms = int((time.time() - started) * 1000),
                                              cost_usd    = result.cost_usd,
                                              identity    = self.identity,
                                              ts          = time.time()))
        return result
