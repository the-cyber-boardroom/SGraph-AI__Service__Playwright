# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Probe__Executor (Φ5 — probe-batch headline feature)
#
# Implements POST /inspect's "snapshot-once, probe-many" pattern (addendum
# §4.1): one navigate + settle, then fan out a named bag of read-only
# probes against the same DOM state. Reuses Sequence__Runner so we get the
# launch / page / listener-buffer / teardown plumbing for free — this class
# is essentially a translator between Inspect__Request shape and
# Sequence__Request shape, plus the reverse for the response.
#
# Read-only verb allowlist: probes can only do non-mutating reads. Caller
# mistakes (e.g. a `click` probe) materialise as a per-probe FAILED with a
# clear error_message, not a crash.
#
# diagnostics_on_fail: when True (default), we ALWAYS append get_console_tail
# + get_network_failures as terminal steps so the buffer is read before
# teardown, but we only EXPOSE them in the response when at least one
# probe / settle / navigate failed. Cheap insurance — diagnostic steps cost
# ~milliseconds; serialising them only when useful keeps the success-path
# response tidy.
# ═══════════════════════════════════════════════════════════════════════════════

import uuid
from typing                                                                                         import Any, Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Request                          import Schema__Inspect__Request
from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Response                         import Schema__Inspect__Response
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Config                         import Schema__Sequence__Config
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Request                        import Schema__Sequence__Request


READ_ONLY_PROBE_ACTIONS = frozenset({                                               # Probes are read-only by contract; mutations belong on /sequence/execute
    Enum__Step__Action.GET_URL.value           ,
    Enum__Step__Action.GET_TEXT.value          ,
    Enum__Step__Action.GET_HTML.value          ,
    Enum__Step__Action.GET_CONTENT.value       ,
    Enum__Step__Action.GET_DOM_TREE.value      ,
    Enum__Step__Action.GET_A11Y_TREE.value     ,
    Enum__Step__Action.GET_PDF.value           ,
    Enum__Step__Action.SCREENSHOT.value        ,
    Enum__Step__Action.GET_CONSOLE_TAIL.value  ,
    Enum__Step__Action.GET_NETWORK_FAILURES.value ,
})

_DIAGNOSTICS_KEY__CONSOLE = '__diagnostics_console_tail__'                          # Synthetic step ids for the appended diagnostic steps — distinguish them from caller-named probes
_DIAGNOSTICS_KEY__NETWORK = '__diagnostics_network_failures__'


class Probe__Executor(Type_Safe):

    sequence_runner : Any = None                                                    # Injected by Playwright__Service.setup() — same Sequence__Runner instance used by /sequence/execute (duck-typed for testability)

    def execute(self, request: Schema__Inspect__Request) -> Schema__Inspect__Response:
        # ── Step 1: validate probe names + verbs ──────────────────────────────
        for probe_name, probe_dict in request.probes.items():
            action = probe_dict.get('action')
            if action not in READ_ONLY_PROBE_ACTIONS:
                raise ValueError(f"probes['{probe_name}']: action '{action}' is not a read-only probe verb. "
                                 f"Allowed: {sorted(READ_ONLY_PROBE_ACTIONS)}")

        # ── Step 2: assemble the internal sequence ────────────────────────────
        navigate_dict = request.navigate.json()
        settle_dicts  = list(request.settle or [])
        probe_items   = list(request.probes.items())                                # Preserves dict insertion order — caller can rely on probe order if needed
        steps         = [navigate_dict] + settle_dicts + [d for _, d in probe_items]

        # Always append diagnostic steps when diagnostics_on_fail is True — we
        # need the buffer values BEFORE Sequence__Runner tears down the browser.
        diagnostics_enabled = bool(request.diagnostics_on_fail)
        if diagnostics_enabled:
            steps.append({'action': Enum__Step__Action.GET_CONSOLE_TAIL.value,
                          'id'    : _DIAGNOSTICS_KEY__CONSOLE                 ,
                          'lines' : 200                                       })
            steps.append({'action': Enum__Step__Action.GET_NETWORK_FAILURES.value,
                          'id'    : _DIAGNOSTICS_KEY__NETWORK                     })

        # ── Step 3: run via Sequence__Runner ──────────────────────────────────
        trace_id    = request.trace_id or Safe_Str__Trace_Id(uuid.uuid4().hex[:8])
        seq_request = Schema__Sequence__Request(
            sequence_id     = Sequence_Id()                                                      ,
            trace_id        = trace_id                                                           ,
            browser_config  = request.browser_config                                             ,
            credentials     = request.credentials                                                ,
            capture_config  = request.capture_config or Schema__Capture__Config()                ,
            sequence_config = Schema__Sequence__Config()                                         ,    # No halt_on_error — probes are independent; one failure shouldn't skip the rest
            steps           = steps                                                              ,
        )
        seq_response = self.sequence_runner.execute(seq_request)

        # ── Step 4: split results back into navigate / settle / probes ────────
        results          = list(seq_response.step_results)
        navigate_result  = results[0] if results else None
        settle_results   = results[1 : 1 + len(settle_dicts)]
        probes_offset    = 1 + len(settle_dicts)
        probe_slice      = results[probes_offset : probes_offset + len(probe_items)]
        probe_results    = {name: probe_slice[i] for i, (name, _) in enumerate(probe_items)}

        # ── Step 5: surface diagnostics only when at least one failure occurred ─
        diagnostics = None
        if diagnostics_enabled:
            had_failure = self._had_failure(navigate_result, settle_results, probe_slice)
            if had_failure:
                diagnostics = self._extract_diagnostics(results)                                   # Read from the last 2 (appended) step results

        return Schema__Inspect__Response(inspect_id        = seq_response.sequence_id                ,
                                          trace_id          = seq_response.trace_id                   ,
                                          status            = seq_response.status                     ,
                                          engine            = seq_response.engine                     ,
                                          total_duration_ms = seq_response.total_duration_ms          ,
                                          navigate_result   = navigate_result                         ,
                                          settle_results    = settle_results                          ,
                                          probe_results     = probe_results                           ,
                                          diagnostics       = diagnostics                             ,
                                          artefacts         = list(seq_response.artefacts)            ,
                                          timings           = seq_response.timings                    )

    def _had_failure(self, navigate_result, settle_results: List, probe_results: List) -> bool:
        if navigate_result is not None and navigate_result.status == Enum__Step__Status.FAILED:
            return True
        for r in list(settle_results) + list(probe_results):
            if r.status == Enum__Step__Status.FAILED:
                return True
        return False

    def _extract_diagnostics(self, all_results: List[Schema__Step__Result__Base]) -> Dict:        # The last two appended steps carry the buffers
        console_log     : List = []
        network_failures: List = []
        for r in all_results:
            sid = str(r.step_id) if r.step_id is not None else ''
            if sid == _DIAGNOSTICS_KEY__CONSOLE and r.console_log is not None:
                console_log = r.console_log
            elif sid == _DIAGNOSTICS_KEY__NETWORK and r.network_failures is not None:
                network_failures = r.network_failures
        return {'console_log': console_log, 'network_failures': network_failures}
