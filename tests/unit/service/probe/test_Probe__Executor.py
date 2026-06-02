# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Probe__Executor (Φ5 — /inspect probe-batch)
#
# Uses a Fake__Sequence__Runner that records the assembled sequence + returns
# a canned response — proves Probe__Executor's TRANSLATION layer (request
# shape, result splitting, diagnostics gating) without needing real Chromium.
# ═══════════════════════════════════════════════════════════════════════════════

from typing  import List
from unittest import TestCase

from osbot_utils.type_safe.primitives.core.Safe_UInt                                          import Safe_UInt

from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                          import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                              import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                              import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Request                      import Schema__Inspect__Request
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id             import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id                    import Sequence_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                        import Step_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds            import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                    import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Request                    import Schema__Sequence__Request
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response                   import Schema__Sequence__Response
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings                    import Schema__Sequence__Timings
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                          import Schema__Step__Navigate
from sg_compute_specs.playwright.core.service.probe.Probe__Executor                                 import (
    Probe__Executor, _DIAGNOSTICS_KEY__CONSOLE, _DIAGNOSTICS_KEY__NETWORK)


def _passed_result(step_index: int, action: Enum__Step__Action, step_id: str = None, **lifted) -> Schema__Step__Result__Base:
    return Schema__Step__Result__Base(step_id     = Step_Id(step_id or str(step_index)),
                                      step_index  = Safe_UInt(step_index)              ,
                                      action      = action                             ,
                                      status      = Enum__Step__Status.PASSED          ,
                                      duration_ms = Safe_UInt__Milliseconds(10)        ,
                                      **lifted                                         )


def _failed_result(step_index: int, action: Enum__Step__Action, step_id: str = None) -> Schema__Step__Result__Base:
    return Schema__Step__Result__Base(step_id       = Step_Id(step_id or str(step_index))    ,
                                      step_index    = Safe_UInt(step_index)                  ,
                                      action        = action                                 ,
                                      status        = Enum__Step__Status.FAILED              ,
                                      duration_ms   = Safe_UInt__Milliseconds(10)            ,
                                      error_message = 'simulated'                            )


def _seq_response(step_results: List[Schema__Step__Result__Base], status=Enum__Sequence__Status.COMPLETED) -> Schema__Sequence__Response:
    return Schema__Sequence__Response(sequence_id       = Sequence_Id()                       ,
                                       trace_id          = Safe_Str__Trace_Id('abcdef01')      ,
                                       status            = status                              ,
                                       total_duration_ms = Safe_UInt__Milliseconds(100)        ,
                                       steps_total       = Safe_UInt(len(step_results))        ,
                                       steps_passed      = Safe_UInt(sum(1 for r in step_results if r.status == Enum__Step__Status.PASSED)),
                                       steps_failed      = Safe_UInt(sum(1 for r in step_results if r.status == Enum__Step__Status.FAILED)),
                                       steps_skipped     = Safe_UInt(0)                        ,
                                       step_results      = step_results                        ,
                                       artefacts         = []                                  ,
                                       timings           = Schema__Sequence__Timings()         )


class _Fake_Sequence_Runner:                                                              # Callable — matches Probe__Executor.run_sequence (asyncio-safe wrapper) signature
    def __init__(self, response: Schema__Sequence__Response):
        self.response          = response
        self.last_request: Schema__Sequence__Request = None

    def __call__(self, request: Schema__Sequence__Request) -> Schema__Sequence__Response:
        self.last_request = request
        return self.response


# ── Tests ────────────────────────────────────────────────────────────────────

class test_validation(TestCase):

    def test__mutating_probe_action_raises_ValueError(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'do_click': {'action': 'click', 'selector': 'a'}})
        executor = Probe__Executor(run_sequence=_Fake_Sequence_Runner(_seq_response([])))
        with self.assertRaises(ValueError) as cm:
            executor.execute(req)
        assert "'click' is not a read-only probe verb" in str(cm.exception)
        assert 'do_click' in str(cm.exception)

    def test__navigate_probe_is_rejected_too(self):                                       # Navigate belongs in the top-level `navigate` field, not in probes
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'p1': {'action': 'navigate', 'url': 'https://x'}})
        executor = Probe__Executor(run_sequence=_Fake_Sequence_Runner(_seq_response([])))
        with self.assertRaises(ValueError):
            executor.execute(req)


class test_sequence_assembly(TestCase):

    def test__assembled_sequence_is_navigate_settle_probes_diagnostics(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[{'action': 'wait_for', 'state': 'load'}]         ,
                                        probes  ={'url':  {'action': 'get_url' }            ,
                                                  'text': {'action': 'get_text'}            },
                                        diagnostics_on_fail=True                                   )
        runner   = _Fake_Sequence_Runner(_seq_response([_passed_result(0, Enum__Step__Action.NAVIGATE),
                                                        _passed_result(1, Enum__Step__Action.WAIT_FOR),
                                                        _passed_result(2, Enum__Step__Action.GET_URL),
                                                        _passed_result(3, Enum__Step__Action.GET_TEXT),
                                                        _passed_result(4, Enum__Step__Action.GET_CONSOLE_TAIL,    step_id=_DIAGNOSTICS_KEY__CONSOLE),
                                                        _passed_result(5, Enum__Step__Action.GET_NETWORK_FAILURES, step_id=_DIAGNOSTICS_KEY__NETWORK)]))
        executor = Probe__Executor(run_sequence=runner)
        executor.execute(req)

        steps = runner.last_request.steps
        assert len(steps) == 6                                                                # navigate + 1 settle + 2 probes + 2 diagnostics
        assert steps[0]['action'] == 'navigate'
        assert steps[1]['action'] == 'wait_for'
        assert steps[2]['action'] == 'get_url'
        assert steps[3]['action'] == 'get_text'
        assert steps[4]['action'] == 'get_console_tail'      and steps[4]['id'] == _DIAGNOSTICS_KEY__CONSOLE
        assert steps[5]['action'] == 'get_network_failures'  and steps[5]['id'] == _DIAGNOSTICS_KEY__NETWORK

    def test__diagnostics_disabled_skips_appended_steps(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'url': {'action': 'get_url'}}                     ,
                                        diagnostics_on_fail=False                                   )
        runner   = _Fake_Sequence_Runner(_seq_response([_passed_result(0, Enum__Step__Action.NAVIGATE),
                                                        _passed_result(1, Enum__Step__Action.GET_URL)]))
        Probe__Executor(run_sequence=runner).execute(req)
        steps = runner.last_request.steps
        assert len(steps) == 2                                                                # No diagnostic tails appended
        assert all(s.get('id') not in (_DIAGNOSTICS_KEY__CONSOLE, _DIAGNOSTICS_KEY__NETWORK) for s in steps)


class test_result_splitting(TestCase):

    def test__results_split_into_navigate_settle_and_named_probes(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[{'action': 'wait_for', 'state': 'load'}]         ,
                                        probes  ={'url':  {'action': 'get_url'} ,
                                                  'text': {'action': 'get_text'}},
                                        diagnostics_on_fail=False                                   )
        runner   = _Fake_Sequence_Runner(_seq_response([_passed_result(0, Enum__Step__Action.NAVIGATE, url='https://example.com/'),
                                                        _passed_result(1, Enum__Step__Action.WAIT_FOR),
                                                        _passed_result(2, Enum__Step__Action.GET_URL,  url='https://example.com/'),
                                                        _passed_result(3, Enum__Step__Action.GET_TEXT, text='Hello')]))
        resp = Probe__Executor(run_sequence=runner).execute(req)

        assert resp.navigate_result.action == Enum__Step__Action.NAVIGATE
        assert len(resp.settle_results)   == 1
        assert set(resp.probe_results.keys()) == {'url', 'text'}
        assert str(resp.probe_results['url'].url)  == 'https://example.com/'
        assert str(resp.probe_results['text'].text) == 'Hello'

    def test__empty_settle_list_yields_empty_settle_results(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'url': {'action': 'get_url'}}                     ,
                                        diagnostics_on_fail=False                                   )
        runner   = _Fake_Sequence_Runner(_seq_response([_passed_result(0, Enum__Step__Action.NAVIGATE),
                                                        _passed_result(1, Enum__Step__Action.GET_URL)]))
        resp = Probe__Executor(run_sequence=runner).execute(req)
        assert resp.settle_results == []
        assert 'url' in resp.probe_results


class test_diagnostics(TestCase):

    def test__diagnostics_populated_on_failure_when_enabled(self):
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'broken': {'action': 'get_url'}}                  ,
                                        diagnostics_on_fail=True                                    )
        runner   = _Fake_Sequence_Runner(_seq_response([
            _passed_result(0, Enum__Step__Action.NAVIGATE),
            _failed_result(1, Enum__Step__Action.GET_URL),
            _passed_result(2, Enum__Step__Action.GET_CONSOLE_TAIL,    step_id=_DIAGNOSTICS_KEY__CONSOLE,    console_log=[{'type': 'error', 'text': 'oops'}]),
            _passed_result(3, Enum__Step__Action.GET_NETWORK_FAILURES, step_id=_DIAGNOSTICS_KEY__NETWORK,    network_failures=[{'url': 'https://blocked/'}]),
        ], status=Enum__Sequence__Status.FAILED))
        resp = Probe__Executor(run_sequence=runner).execute(req)

        assert resp.diagnostics is not None
        assert resp.diagnostics['console_log']     == [{'type': 'error', 'text': 'oops'}]
        assert resp.diagnostics['network_failures'] == [{'url': 'https://blocked/'}]

    def test__diagnostics_null_on_success_path(self):                                          # Even with diagnostics_on_fail=True, no failure = no diagnostics in response
        req = Schema__Inspect__Request(navigate=Schema__Step__Navigate(url='https://example.com'),
                                        settle  =[]                                                ,
                                        probes  ={'url': {'action': 'get_url'}}                     ,
                                        diagnostics_on_fail=True                                    )
        runner   = _Fake_Sequence_Runner(_seq_response([
            _passed_result(0, Enum__Step__Action.NAVIGATE),
            _passed_result(1, Enum__Step__Action.GET_URL),
            _passed_result(2, Enum__Step__Action.GET_CONSOLE_TAIL,    step_id=_DIAGNOSTICS_KEY__CONSOLE,    console_log=[]),
            _passed_result(3, Enum__Step__Action.GET_NETWORK_FAILURES, step_id=_DIAGNOSTICS_KEY__NETWORK,    network_failures=[]),
        ]))
        resp = Probe__Executor(run_sequence=runner).execute(req)
        assert resp.diagnostics is None
