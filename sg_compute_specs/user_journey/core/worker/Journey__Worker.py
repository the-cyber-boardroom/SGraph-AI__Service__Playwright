# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Journey__Worker (one journey run, in-process)
#
# Composes the reused parts into one run: build a sequence request, execute it via
# the substrate Playwright core (so Step__Executor stays the only page.* caller),
# pull this run's flows from the mitmproxy capture, evaluate assertions, and
# assemble a Schema__Journey__Result. `run()` is the integration path (needs a real
# browser + mitmproxy, exercised under the gated deploy tests); derive_status and
# assemble_result are pure and unit-tested here.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sg_compute_specs.user_journey.core.evaluator.Journey__Assertion__Evaluator                         import Journey__Assertion__Evaluator
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status                            import Enum__Assertion__Status
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Journey__Run__Status                         import Enum__Journey__Run__Status
from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Result                          import Schema__Journey__Result
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Run_Id                           import Run_Id
from sg_compute_specs.user_journey.core.worker.Journey__Sequence__Builder                                import Journey__Sequence__Builder


class Journey__Worker(Type_Safe):                                                   # runs one journey end-to-end

    def run(self, journey, run_id, playwright_service, capture_client=None) -> Schema__Journey__Result:
        started_at        = Timestamp_Now()
        request           = Journey__Sequence__Builder().build(journey, run_id)
        sequence_response = playwright_service.execute_sequence(request)            # reused core; Step__Executor owns page.*
        network_log       = capture_client.network_log(run_id) if capture_client else []
        assertion_results = Journey__Assertion__Evaluator().evaluate(list(journey.assertions), sequence_response, network_log)
        ended_at          = Timestamp_Now()
        return self.assemble_result(run_id, journey, sequence_response, assertion_results, started_at, ended_at)

    def derive_status(self, assertion_results: List) -> Enum__Journey__Run__Status:
        statuses = [result.status for result in assertion_results]
        if Enum__Assertion__Status.FAILED in statuses:                              # a definite failure wins
            return Enum__Journey__Run__Status.FAILED
        if Enum__Assertion__Status.ERROR in statuses:                               # else an indeterminate evaluation
            return Enum__Journey__Run__Status.ERROR
        return Enum__Journey__Run__Status.PASSED

    def assemble_result(self, run_id, journey, sequence_response, assertion_results,
                              started_at=None, ended_at=None) -> Schema__Journey__Result:
        result = Schema__Journey__Result(status=self.derive_status(assertion_results))
        if run_id              is not None: result.run_id            = Run_Id(str(run_id))
        if journey.journey_id  is not None: result.journey_id        = journey.journey_id
        if journey.environment is not None: result.environment       = journey.environment
        if sequence_response   is not None: result.sequence_response = sequence_response
        if started_at          is not None: result.started_at        = started_at
        if ended_at            is not None: result.ended_at          = ended_at
        for assertion_result in assertion_results:
            result.assertion_results.append(assertion_result)
        return result
