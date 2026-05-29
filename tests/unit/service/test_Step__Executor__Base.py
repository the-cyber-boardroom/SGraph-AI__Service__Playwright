# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Step__Executor__Base
#
# Locks the engine-neutral extraction: the base owns result-building, error
# classification, id/ref helpers, and the dispatch-table lookup — independent of
# any page.*. The sync Step__Executor (and the future async leaf) inherit it.
# Behavioural coverage of the helpers lives in test_Step__Executor.py (exercised
# through the sync leaf); this file pins the structure + standalone behaviour.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                          import TestCase

from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                    import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Error__Type               import Enum__Step__Error__Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                     import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Get_Url                  import Schema__Step__Get_Url
from sg_compute_specs.playwright.core.service.Artefact__Writer                             import Artefact__Writer
from sg_compute_specs.playwright.core.service.Step__Executor                               import Step__Executor
from sg_compute_specs.playwright.core.service.Step__Executor__Base                         import ACTION_HANDLERS, Step__Executor__Base


class test_extraction_shape(TestCase):

    def test__sync_executor_inherits_the_base(self):
        assert issubclass(Step__Executor, Step__Executor__Base)

    def test__base_composes_artefact_writer(self):
        assert isinstance(Step__Executor__Base().artefact_writer, Artefact__Writer)

    def test__action_handlers_lives_on_the_base(self):                                  # single source of truth, re-exported from the sync module
        assert ACTION_HANDLERS[Enum__Step__Action.NAVIGATE] == 'execute_navigate'


class test_base_helpers_standalone(TestCase):

    def test__handler_name_maps_known_action(self):
        step = Schema__Step__Get_Url()
        assert Step__Executor__Base().handler_name(step) == 'execute_get_url'

    def test__handler_name_none_for_unmapped(self):
        step = Schema__Step__Get_Url()
        step.action = Enum__Step__Action.VIDEO_START                                    # not in ACTION_HANDLERS
        assert Step__Executor__Base().handler_name(step) is None

    def test__passed_result_shape(self):
        step = Schema__Step__Get_Url()
        res  = Step__Executor__Base().passed_result(step, step_index=3, started_ms=0)
        assert res.status     == Enum__Step__Status.PASSED
        assert res.step_index == 3
        assert str(res.step_id) == '3'                                                  # falls back to ordinal

    def test__failed_result_classifies(self):
        step = Schema__Step__Get_Url()
        res  = Step__Executor__Base().failed_result(step, 0, 0, TimeoutError('Timeout 30000ms exceeded'))
        assert res.status     == Enum__Step__Status.FAILED
        assert res.error_type == Enum__Step__Error__Type.TIMEOUT
