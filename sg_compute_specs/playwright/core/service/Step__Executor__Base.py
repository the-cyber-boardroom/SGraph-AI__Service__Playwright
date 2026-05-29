# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Step__Executor__Base
#
# Engine-neutral foundation shared by the sync Step__Executor and the async
# Step__Executor__Async. Holds everything that does NOT touch page.* :
#   • result constructors (passed / failed / skipped)
#   • error classification (exception → Enum__Step__Error__Type)
#   • step-id resolution + artefact-ref filtering
#   • the wall-clock seam (now_ms)
#   • handler-name lookup against ACTION_HANDLERS
#
# The only thing the two leaves implement differently is the body of each
# execute_{action} method — sync `page.goto(...)` vs async `await page.goto(...)`.
# This keeps ~85% of executor logic in one place; the page-touching surface (the
# rule-#16 boundary) stays in the two leaf classes.
#
# ACTION_HANDLERS lives here (single source of truth) and is imported by both
# leaves and by the dispatchers.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                                         import List, Optional

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Error__Type                             import Enum__Step__Error__Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base
from sg_compute_specs.playwright.core.service.Artefact__Writer                                          import Artefact__Writer


# Action → handler-method name. Single source of truth for dispatch; reused by
# both the sync and async executors. An action absent from this table resolves to
# a clean per-step FAILED result, never an exception that aborts the sequence.
# VIDEO_START / VIDEO_STOP are intentionally absent — recording is a context-level
# concern handled via capture_config.video, not a per-step verb.
ACTION_HANDLERS = {
    Enum__Step__Action.NAVIGATE       : 'execute_navigate'       ,
    Enum__Step__Action.CLICK          : 'execute_click'          ,
    Enum__Step__Action.FILL           : 'execute_fill'           ,
    Enum__Step__Action.SCREENSHOT     : 'execute_screenshot'     ,
    Enum__Step__Action.GET_CONTENT    : 'execute_get_content'    ,
    Enum__Step__Action.GET_URL        : 'execute_get_url'        ,
    Enum__Step__Action.EVALUATE       : 'execute_evaluate'       ,
    Enum__Step__Action.WAIT_FOR       : 'execute_wait_for'       ,
    Enum__Step__Action.PRESS          : 'execute_press'          ,
    Enum__Step__Action.SELECT         : 'execute_select'         ,
    Enum__Step__Action.HOVER          : 'execute_hover'          ,
    Enum__Step__Action.SCROLL         : 'execute_scroll'         ,
    Enum__Step__Action.SET_VIEWPORT   : 'execute_set_viewport'   ,
    Enum__Step__Action.DISPATCH_EVENT : 'execute_dispatch_event' ,
}


class Step__Executor__Base(Type_Safe):

    artefact_writer : Artefact__Writer

    # ─── Dispatch lookup (engine-neutral) ──────────────────────────────────────

    def handler_name(self, step: Schema__Step__Base) -> Optional[str]:                  # None → unsupported action (caller returns a FAILED result)
        return ACTION_HANDLERS.get(step.action)

    # ─── Result constructors ───────────────────────────────────────────────────

    def passed_result(self                                          ,
                      step       : Schema__Step__Base               ,
                      step_index : int                              ,
                      started_ms : int                              ,
                      artefacts  : List[Schema__Artefact__Ref] = None
                 ) -> Schema__Step__Result__Base:
        return Schema__Step__Result__Base(step_id     = self.resolve_id(step, step_index) ,
                                          step_index  = step_index                        ,
                                          action      = step.action                       ,
                                          status      = Enum__Step__Status.PASSED         ,
                                          duration_ms = self.now_ms() - started_ms        ,
                                          artefacts   = artefacts or []                   )

    def failed_result(self                                          ,
                      step       : Schema__Step__Base               ,
                      step_index : int                              ,
                      started_ms : int                              ,
                      error      : Exception
                 ) -> Schema__Step__Result__Base:
        return Schema__Step__Result__Base(step_id       = self.resolve_id(step, step_index) ,
                                          step_index    = step_index                        ,
                                          action        = step.action                       ,
                                          status        = Enum__Step__Status.FAILED         ,
                                          duration_ms   = self.now_ms() - started_ms        ,
                                          error_message = Safe_Str__Text(str(error)[:1000]) ,
                                          error_type    = self.classify_error(error)        ,
                                          artefacts     = []                                )

    def classify_error(self, error: Exception) -> Enum__Step__Error__Type:              # Map an exception to a structured category. Recognise Playwright's TimeoutError by name to avoid an import-time dependency on the sync/async API module.
        cls       = type(error).__name__
        msg_lower = str(error).lower()
        if 'timeout' in cls.lower() or 'timeout' in msg_lower:
            return Enum__Step__Error__Type.TIMEOUT
        if isinstance(error, NotImplementedError):
            return Enum__Step__Error__Type.UNSUPPORTED_ACTION
        if 'allowlist' in msg_lower or 'not allowed' in msg_lower:                       # JS__Expression__Allowlist denial
            return Enum__Step__Error__Type.EVALUATE_REJECTED
        if 'ERR_NAME_NOT_RESOLVED' in str(error) or 'net::' in str(error) or 'navigation' in msg_lower:
            return Enum__Step__Error__Type.NAVIGATION_FAILED
        if 'selector' in msg_lower and ('not found' in msg_lower or 'no element' in msg_lower or 'no node' in msg_lower):
            return Enum__Step__Error__Type.SELECTOR_NOT_FOUND
        return Enum__Step__Error__Type.UNKNOWN

    def resolve_id(self, step: Schema__Step__Base, step_index: int) -> Step_Id:         # Fall back to the ordinal when caller didn't provide id
        return step.id if step.id is not None else Step_Id(str(step_index))

    def filter_refs(self, refs: List[Schema__Artefact__Ref]) -> List[Schema__Artefact__Ref]:
        return [r for r in refs if r is not None]                                       # Drop None refs (sink_config.enabled=False)

    def now_ms(self) -> int:                                                            # Single wall-clock seam — tests subclass to freeze time
        return int(time.time() * 1000)
