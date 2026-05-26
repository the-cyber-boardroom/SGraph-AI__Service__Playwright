# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Result__Aggregator (counts, suite state, latency percentiles)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.conductor.Result__Aggregator          import Result__Aggregator
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State  import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State      import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status   import Schema__Worker__Status


def _worker(state, started=None, finished=None):
    worker = Schema__Worker__Status(state=state)
    if started  is not None: worker.started_at  = started
    if finished is not None: worker.finished_at = finished
    return worker


class TestCounts:

    def test__tallies_by_state(self):
        workers = [_worker(Enum__Worker__State.PASSED), _worker(Enum__Worker__State.PASSED),
                   _worker(Enum__Worker__State.FAILED), _worker(Enum__Worker__State.RUNNING),
                   _worker(Enum__Worker__State.ERROR),  _worker(Enum__Worker__State.STOPPED)]
        counts = Result__Aggregator().counts(workers)
        assert int(counts.passed)  == 2
        assert int(counts.failed)  == 1
        assert int(counts.running) == 1
        assert int(counts.error)   == 2                                             # ERROR + STOPPED


class TestState:

    def test__empty_is_pending(self):
        assert Result__Aggregator().state([]) == Enum__Suite__Run__State.PENDING

    def test__all_pending_is_pending(self):
        workers = [_worker(Enum__Worker__State.PENDING), _worker(Enum__Worker__State.PENDING)]
        assert Result__Aggregator().state(workers) == Enum__Suite__Run__State.PENDING

    def test__any_running_is_running(self):
        workers = [_worker(Enum__Worker__State.PASSED), _worker(Enum__Worker__State.RUNNING)]
        assert Result__Aggregator().state(workers) == Enum__Suite__Run__State.RUNNING

    def test__all_passed_is_done(self):
        workers = [_worker(Enum__Worker__State.PASSED), _worker(Enum__Worker__State.PASSED)]
        assert Result__Aggregator().state(workers) == Enum__Suite__Run__State.DONE

    def test__terminal_with_failure_is_failed(self):
        workers = [_worker(Enum__Worker__State.PASSED), _worker(Enum__Worker__State.FAILED)]
        assert Result__Aggregator().state(workers) == Enum__Suite__Run__State.FAILED


class TestPercentiles:

    def test__nearest_rank(self):
        p50, p95, p99 = Result__Aggregator().percentiles([100, 200, 300, 400, 500])
        assert p50 == 300
        assert p95 == 500
        assert p99 == 500

    def test__empty_is_zero(self):
        assert Result__Aggregator().percentiles([]) == (0, 0, 0)


class TestAggregate:

    def test__end_to_end_snapshot(self):
        workers = [_worker(Enum__Worker__State.PASSED, started=1000, finished=1300),   # 300ms
                   _worker(Enum__Worker__State.PASSED, started=2000, finished=2500),   # 500ms
                   _worker(Enum__Worker__State.FAILED, started=3000, finished=3100)]   # 100ms
        status = Result__Aggregator().aggregate(workers, flows_total=42, flows_blocked=3)
        assert status.state                          == Enum__Suite__Run__State.FAILED
        assert int(status.counts.passed)             == 2
        assert int(status.counts.failed)             == 1
        assert len(status.workers)                   == 3
        assert int(status.aggregates.latency_p50_ms) == 300                         # sorted [100,300,500] → p50 idx ceil(1.5)=2 → 300
        assert int(status.aggregates.flows_total)    == 42
        assert int(status.aggregates.flows_blocked)  == 3
