# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Sequence__Dispatcher (v2 spec §4.5; v1 source not in pack)
#
# Thin class wrapper around the parse helpers in dispatcher/step_schema_registry.py.
# Gives Action__Runner and Sequence__Runner a consistent DI surface for:
#   • parse_single_step(step_dict, step_index) — one wire-format step → typed Schema__Step__*
#   • parse_steps       (step_dicts)           — bulk parse
#   • execute_step      (…)                    — deferred to Phase 2.5; needs Step__Executor
#
# The module-level parse helpers stay as-is so the dispatcher registry remains
# the single source of truth for action → schema wiring (spec §8).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.dispatcher.step_schema_registry                                   import parse_step
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Base                                  import Schema__Step__Base


class Sequence__Dispatcher(Type_Safe):

    def parse_single_step(self                    ,
                          step_dict  : dict       ,
                          step_index : int
                     ) -> Schema__Step__Base:
        return parse_step(step_dict, step_index)

    def parse_steps(self, step_dicts: List[dict]) -> List[Schema__Step__Base]:
        return [parse_step(step_dict, index) for index, step_dict in enumerate(step_dicts)]
