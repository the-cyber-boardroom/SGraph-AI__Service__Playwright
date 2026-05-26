# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Suite__Service (conductor lifecycle over the in-memory runtime; no Docker)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.conductor.Suite__Service             import Suite__Service
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__InMemory  import Worker__Runtime__InMemory
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State     import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition import Schema__Suite__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Entry      import Schema__Suite__Entry


def _definition(count=3, concurrency=2):
    definition = Schema__Suite__Definition(suite_id='nightly')
    definition.entries.append(Schema__Suite__Entry(journey_id='checkout', count=count, concurrency=concurrency))
    return definition


class TestStartSuite:

    def test__launches_count_workers_running(self):
        service = Suite__Service().setup()
        status  = service.start_suite(_definition(count=3), default_image='diniscruz/sg-journey-runner:latest',
                                      suite_run_id='run-1')
        assert str(status.suite_run_id)  == 'run-1'
        assert str(status.suite_id)      == 'nightly'
        assert status.state              == Enum__Suite__Run__State.RUNNING
        assert len(status.workers)       == 3
        assert int(status.counts.running) == 3
        assert service.runtime.launched and len(service.runtime.launched) == 3     # runtime actually asked to launch

    def test__stored_and_retrievable(self):
        service = Suite__Service().setup()
        service.start_suite(_definition(count=2), suite_run_id='run-2')
        fetched = service.get_suite('run-2')
        assert fetched is not None
        assert len(fetched.workers) == 2

    def test__auto_generates_run_id_when_omitted(self):
        service = Suite__Service().setup()
        status  = service.start_suite(_definition(count=1))
        assert str(status.suite_run_id).startswith('nightly-')


class TestReportWorker:

    def test__report_drives_counts_and_done_state(self):
        service = Suite__Service().setup()
        status  = service.start_suite(_definition(count=2), suite_run_id='run-3')
        worker_ids = [str(w.worker_id) for w in status.workers]

        service.report_worker('run-3', worker_ids[0], Enum__Worker__State.PASSED)
        mid = service.get_suite('run-3')
        assert mid.state              == Enum__Suite__Run__State.RUNNING            # one still running
        assert int(mid.counts.passed) == 1

        service.report_worker('run-3', worker_ids[1], Enum__Worker__State.PASSED)
        done = service.get_suite('run-3')
        assert done.state             == Enum__Suite__Run__State.DONE               # all terminal, none failed
        assert int(done.counts.passed) == 2

    def test__a_failure_makes_suite_failed(self):
        service = Suite__Service().setup()
        status  = service.start_suite(_definition(count=2), suite_run_id='run-4')
        ids     = [str(w.worker_id) for w in status.workers]
        service.report_worker('run-4', ids[0], Enum__Worker__State.PASSED)
        service.report_worker('run-4', ids[1], Enum__Worker__State.FAILED)
        assert service.get_suite('run-4').state == Enum__Suite__Run__State.FAILED


class TestStopSuite:

    def test__stop_marks_inflight_workers_stopped(self):
        service = Suite__Service().setup()
        service.start_suite(_definition(count=3), suite_run_id='run-5')
        stopped = service.stop_suite('run-5')
        assert stopped.state == Enum__Suite__Run__State.STOPPED
        assert all(w.state == Enum__Worker__State.STOPPED for w in stopped.workers)

    def test__unknown_run_returns_none(self):
        assert Suite__Service().setup().stop_suite('nope')      is None
        assert Suite__Service().setup().get_suite('nope')       is None


class TestRuntimeInjection:

    def test__setup_defaults_to_in_memory_runtime(self):
        service = Suite__Service().setup()
        assert isinstance(service.runtime, Worker__Runtime__InMemory)
