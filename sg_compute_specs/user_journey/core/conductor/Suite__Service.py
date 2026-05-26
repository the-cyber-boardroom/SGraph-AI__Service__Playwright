# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Suite__Service (the conductor's brain)
#
# Ties the planner + aggregator + launch port into the suite lifecycle the
# conductor API exposes. start_suite plans waves and launches each worker via the
# runtime; get_suite re-aggregates the live worker statuses; report_worker lands a
# worker's terminal verdict (workers POST back); stop_suite stops in-flight workers.
# Pure of Docker/HTTP — the runtime port + the in-memory store make it unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.user_journey.core.conductor.Result__Aggregator           import Result__Aggregator
from sg_compute_specs.user_journey.core.conductor.Suite__Runner                import Suite__Runner
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime              import Worker__Runtime
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__InMemory    import Worker__Runtime__InMemory
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State   import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State        import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status


class Suite__Service(Type_Safe):
    runner     : Suite__Runner
    aggregator : Result__Aggregator
    runtime    : Worker__Runtime = None                                             # defaults to in-memory in setup()
    runs       : Dict[str, Schema__Suite__Run__Status]                              # suite_run_id → live snapshot

    def setup(self) -> 'Suite__Service':
        if self.runtime is None:
            self.runtime = Worker__Runtime__InMemory()
        return self

    def start_suite(self, definition, default_image=None, suite_run_id=None) -> Schema__Suite__Run__Status:
        run_id  = str(suite_run_id) if suite_run_id else self._next_id(definition)
        workers = []
        for wave in self.runner.plan(definition, default_image):
            for spec in wave:
                workers.append(self.runtime.launch(spec))
        status = self._snapshot(run_id, definition.suite_id, workers)
        self.runs[run_id] = status
        return status

    def get_suite(self, suite_run_id):
        return self.runs.get(str(suite_run_id))

    def report_worker(self, suite_run_id, worker_id, state: Enum__Worker__State):
        status = self.runs.get(str(suite_run_id))
        if status is None:
            return None
        for worker in status.workers:
            if str(worker.worker_id) == str(worker_id):
                worker.state = state
        refreshed = self._reaggregate(status)
        self.runs[str(suite_run_id)] = refreshed
        return refreshed

    def stop_suite(self, suite_run_id):
        status = self.runs.get(str(suite_run_id))
        if status is None:
            return None
        for worker in status.workers:
            if worker.state in (Enum__Worker__State.PENDING, Enum__Worker__State.RUNNING):
                self.runtime.stop(worker)
        refreshed       = self._reaggregate(status)
        refreshed.state = Enum__Suite__Run__State.STOPPED                           # operator-stopped, regardless of tally
        self.runs[str(suite_run_id)] = refreshed
        return refreshed

    # ── helpers ────────────────────────────────────────────────────────────────
    def _snapshot(self, suite_run_id, suite_id, workers) -> Schema__Suite__Run__Status:
        status              = self.aggregator.aggregate(workers)
        status.suite_run_id = suite_run_id
        if suite_id is not None:
            status.suite_id = suite_id
        return status

    def _reaggregate(self, previous: Schema__Suite__Run__Status) -> Schema__Suite__Run__Status:
        status              = self.aggregator.aggregate(list(previous.workers))
        status.suite_run_id = previous.suite_run_id
        status.suite_id     = previous.suite_id
        return status

    def _next_id(self, definition) -> str:
        base = str(definition.suite_id) if definition.suite_id is not None else 'suite'
        return f'{base}-{len(self.runs) + 1:04d}'
