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

from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                      import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Engine                               import Enum__Engine
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                     import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                         import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                         import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id        import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id               import Sequence_Id
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Page__Content          import Safe_Str__Page__Content
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive        import Safe_Str__Url__Permissive
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Evaluate           import Schema__Step__Result__Evaluate
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Content        import Schema__Step__Result__Get_Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url            import Schema__Step__Result__Get_Url
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


# ─── BUG-2 (debrief 2026-05-30) — subclass-specific result fields must survive serialisation ───
# Schema__Sequence__Response.step_results is typed `List[Schema__Step__Result__Base]`.
# Pre-fix: FastAPI/Pydantic narrowed each item to Base and dropped content / url /
# return_value etc. Post-fix: those fields now live on Base (lifted; optional) so a
# Base-typed list serialises them when the actual instance is a subclass.
class test_polymorphic_step_results_serialisation(TestCase):

    def test__get_content_result_preserves_content_after_round_trip(self):
        get_content = Schema__Step__Result__Get_Content(
            step_id        = '0'                                              ,
            step_index     = 0                                                ,
            action         = Enum__Step__Action.GET_CONTENT                   ,
            status         = Enum__Step__Status.PASSED                        ,
            duration_ms    = 50                                               ,
            artefacts      = []                                               ,
            content        = Safe_Str__Page__Content('<html>hello</html>')   ,
            content_format = Enum__Content__Format.HTML                       ,
        )
        response  = _minimal_response(step_results=[get_content])
        as_json   = response.json()
        item_json = as_json['step_results'][0]
        assert item_json.get('content')         == '<html>hello</html>'
        assert item_json.get('content_format')  == 'html'
        restored  = Schema__Sequence__Response.from_json(as_json)
        assert str(restored.step_results[0].content) == '<html>hello</html>'

    def test__get_url_result_preserves_url_after_round_trip(self):              # BUG-1 + BUG-2 together — vault URL with ':' in fragment survives both validation AND polymorphic serialisation
        vault_url = 'https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b'
        get_url = Schema__Step__Result__Get_Url(
            step_id     = '0'                                                 ,
            step_index  = 0                                                   ,
            action      = Enum__Step__Action.GET_URL                          ,
            status      = Enum__Step__Status.PASSED                           ,
            duration_ms = 5                                                   ,
            artefacts   = []                                                  ,
            url         = Safe_Str__Url__Permissive(vault_url)                ,
        )
        response = _minimal_response(step_results=[get_url])
        as_json  = response.json()
        assert as_json['step_results'][0].get('url') == vault_url

    def test__evaluate_result_preserves_return_value(self):                    # FR-5a — evaluate's return_value + return_type survive serialisation
        evaluate = Schema__Step__Result__Evaluate(
            step_id      = '0'                                                ,
            step_index   = 0                                                  ,
            action       = Enum__Step__Action.EVALUATE                        ,
            status       = Enum__Step__Status.PASSED                          ,
            duration_ms  = 3                                                  ,
            artefacts    = []                                                 ,
            return_value = 'Example Domain'                                   ,
            return_type  = Enum__Evaluate__Return_Type.STRING                 ,
        )
        response = _minimal_response(step_results=[evaluate])
        as_json  = response.json()
        item     = as_json['step_results'][0]
        assert item.get('return_value') == 'Example Domain'
        assert item.get('return_type')  == 'string'
