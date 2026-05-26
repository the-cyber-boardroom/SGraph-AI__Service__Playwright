# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Result__Aggregator (roll worker statuses into a suite snapshot)
#
# Pure logic: tally worker states into counts, derive the suite run state, and
# compute latency percentiles (nearest-rank) from worker durations. Produces the
# Schema__Suite__Run__Status the conductor API returns and the cockpit renders.
# ═══════════════════════════════════════════════════════════════════════════════

import math
from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State                           import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State                                import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Counts                             import Schema__Suite__Counts
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status                        import Schema__Suite__Run__Status

TERMINAL_STATES    = (Enum__Worker__State.PASSED, Enum__Worker__State.FAILED, Enum__Worker__State.ERROR, Enum__Worker__State.STOPPED)
FAILED_LIKE_STATES = (Enum__Worker__State.FAILED, Enum__Worker__State.ERROR, Enum__Worker__State.STOPPED)


class Result__Aggregator(Type_Safe):                                                # worker statuses → suite snapshot

    def counts(self, worker_statuses: List) -> Schema__Suite__Counts:
        counts = Schema__Suite__Counts()
        for worker in worker_statuses:
            state = worker.state
            if   state == Enum__Worker__State.PENDING: counts.pending = int(counts.pending) + 1
            elif state == Enum__Worker__State.RUNNING: counts.running = int(counts.running) + 1
            elif state == Enum__Worker__State.PASSED : counts.passed  = int(counts.passed ) + 1
            elif state == Enum__Worker__State.FAILED : counts.failed  = int(counts.failed ) + 1
            else                                     : counts.error   = int(counts.error  ) + 1  # ERROR / STOPPED
        return counts

    def state(self, worker_statuses: List) -> Enum__Suite__Run__State:
        if not worker_statuses:
            return Enum__Suite__Run__State.PENDING
        states = [worker.state for worker in worker_statuses]
        if all(state == Enum__Worker__State.PENDING for state in states):
            return Enum__Suite__Run__State.PENDING
        if any(state in (Enum__Worker__State.PENDING, Enum__Worker__State.RUNNING) for state in states):
            return Enum__Suite__Run__State.RUNNING
        if any(state in FAILED_LIKE_STATES for state in states):
            return Enum__Suite__Run__State.FAILED
        return Enum__Suite__Run__State.DONE

    def durations_ms(self, worker_statuses: List) -> List[int]:
        durations = []
        for worker in worker_statuses:
            if worker.started_at is not None and worker.finished_at is not None:
                durations.append(int(worker.finished_at) - int(worker.started_at))
        return durations

    def percentiles(self, durations_ms: List):                                      # nearest-rank p50 / p95 / p99
        values = sorted(int(duration) for duration in durations_ms if duration is not None)
        if not values:
            return 0, 0, 0
        def at(percentile):
            rank = max(1, math.ceil(percentile / 100 * len(values)))
            return values[rank - 1]
        return at(50), at(95), at(99)

    def aggregate(self, worker_statuses: List, flows_total=0, flows_blocked=0) -> Schema__Suite__Run__Status:
        status        = Schema__Suite__Run__Status(state=self.state(worker_statuses))
        status.counts = self.counts(worker_statuses)
        p50, p95, p99 = self.percentiles(self.durations_ms(worker_statuses))
        status.aggregates.latency_p50_ms = p50
        status.aggregates.latency_p95_ms = p95
        status.aggregates.latency_p99_ms = p99
        status.aggregates.flows_total    = flows_total
        status.aggregates.flows_blocked  = flows_blocked
        for worker in worker_statuses:
            status.workers.append(worker)
        return status
