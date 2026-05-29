# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__Sequence__Response (P1 contract additions)
#
# Covers the two contract additions in v0.2.42:
#   1. `engine` field — reports which execution engine ran (SYNC default; ASYNC
#      when the future async runner produces the response).
#   2. The schema is still Type_Safe — i.e. Routes__Sequence.execute returning
#      `Schema__Sequence__Response` directly (rather than `.json()`) gives
#      FastAPI a typed response_model and replaces the OpenAPI `string`.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                              import TestCase

from sg_compute_specs.playwright.core.schemas.enums.Enum__Engine                               import Enum__Engine
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                     import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id        import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id               import Sequence_Id
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response              import Schema__Sequence__Response
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings               import Schema__Sequence__Timings


def _minimal_response(**overrides) -> Schema__Sequence__Response:
    kwargs = dict(
        sequence_id       = Sequence_Id('safe-id_xxxx')                ,
        trace_id          = Safe_Str__Trace_Id('abcdef01')             ,
        status            = Enum__Sequence__Status.COMPLETED           ,
        total_duration_ms = 100                                        ,
        steps_total       = 1                                          ,
        steps_passed      = 1                                          ,
        steps_failed      = 0                                          ,
        steps_skipped     = 0                                          ,
        step_results      = []                                         ,
        artefacts         = []                                         ,
        timings           = Schema__Sequence__Timings()                ,
    )
    kwargs.update(overrides)
    return Schema__Sequence__Response(**kwargs)


class test_engine_field(TestCase):

    def test__default_is_sync(self):                                                       # backward-compatible default — every existing caller (sync runner) gets SYNC for free
        response = _minimal_response()
        assert response.engine == Enum__Engine.SYNC

    def test__can_be_set_to_async(self):                                                   # the future async runner will pass engine=ASYNC
        response = _minimal_response(engine=Enum__Engine.ASYNC)
        assert response.engine == Enum__Engine.ASYNC

    def test__engine_appears_in_serialised_json(self):                                     # contract: the client sees `engine` in the wire payload
        response = _minimal_response(engine=Enum__Engine.SYNC)
        data     = response.json()
        assert 'engine' in data
        assert data['engine'] == 'sync'


class test_typed_schema_round_trip(TestCase):

    def test__round_trip_preserves_engine(self):
        original = _minimal_response(engine=Enum__Engine.ASYNC)
        as_json  = original.json()
        restored = Schema__Sequence__Response.from_json(as_json)
        assert restored.engine == Enum__Engine.ASYNC
