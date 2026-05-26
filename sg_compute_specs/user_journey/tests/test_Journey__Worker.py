# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Journey__Worker (pure logic: derive_status + assemble_result)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status        import Enum__Assertion__Status
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Journey__Run__Status     import Enum__Journey__Run__Status
from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition   import Schema__Journey__Definition
from sg_compute_specs.user_journey.core.schemas.results.Schema__Journey__Assertion__Result import Schema__Journey__Assertion__Result
from sg_compute_specs.user_journey.core.worker.Journey__Worker                        import Journey__Worker


def _result(status):
    return Schema__Journey__Assertion__Result(status=status)


class TestDeriveStatus:

    def test__all_passed_is_passed(self):
        worker = Journey__Worker()
        statuses = [_result(Enum__Assertion__Status.PASSED), _result(Enum__Assertion__Status.PASSED)]
        assert worker.derive_status(statuses) == Enum__Journey__Run__Status.PASSED

    def test__empty_is_passed(self):
        assert Journey__Worker().derive_status([]) == Enum__Journey__Run__Status.PASSED

    def test__any_failed_is_failed(self):
        worker = Journey__Worker()
        statuses = [_result(Enum__Assertion__Status.PASSED), _result(Enum__Assertion__Status.FAILED)]
        assert worker.derive_status(statuses) == Enum__Journey__Run__Status.FAILED

    def test__any_error_without_failure_is_error(self):
        worker = Journey__Worker()
        statuses = [_result(Enum__Assertion__Status.PASSED), _result(Enum__Assertion__Status.ERROR)]
        assert worker.derive_status(statuses) == Enum__Journey__Run__Status.ERROR

    def test__failure_wins_over_error(self):
        worker = Journey__Worker()
        statuses = [_result(Enum__Assertion__Status.ERROR), _result(Enum__Assertion__Status.FAILED)]
        assert worker.derive_status(statuses) == Enum__Journey__Run__Status.FAILED


class TestAssembleResult:

    def test__assembles_from_journey_and_results(self):
        worker  = Journey__Worker()
        journey = Schema__Journey__Definition(journey_id='login', environment='dev')
        results = [_result(Enum__Assertion__Status.PASSED)]

        result = worker.assemble_result('run-1', journey, None, results)
        assert result.status                 == Enum__Journey__Run__Status.PASSED
        assert str(result.run_id)            == 'run-1'
        assert str(result.journey_id)        == 'login'
        assert str(result.environment)       == 'dev'
        assert len(result.assertion_results) == 1
        assert result.sequence_response      is None

    def test__failed_assertion_makes_failed_result(self):
        worker  = Journey__Worker()
        journey = Schema__Journey__Definition(journey_id='checkout')
        results = [_result(Enum__Assertion__Status.PASSED), _result(Enum__Assertion__Status.FAILED)]

        result = worker.assemble_result('run-2', journey, None, results)
        assert result.status == Enum__Journey__Run__Status.FAILED
