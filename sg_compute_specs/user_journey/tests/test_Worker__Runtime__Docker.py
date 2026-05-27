# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Worker__Runtime__Docker
#
# argv is pure; launch/stop are exercised by a Recording subclass that overrides the
# single subprocess seam (run_docker) — no mocks, no patches, no daemon. Mirrors the
# in-memory backend's contract so Suite__Service is identical above the port.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__Docker     import Worker__Runtime__Docker
from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec import Schema__Worker__Spec
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State       import Enum__Worker__State


class Recording__Docker(Worker__Runtime__Docker):                                   # records argv instead of shelling out
    commands : list

    def run_docker(self, cmd, check=True):
        self.commands.append(list(cmd))
        return None


def _spec():
    spec               = Schema__Worker__Spec()
    spec.worker_id     = 'w1'
    spec.run_id        = 'run-abc'
    spec.journey_id    = 'checkout'
    spec.worker_image  = 'docker.io/sgraph/uj-worker:1.0'
    spec.environment   = 'prod'
    return spec


class TestWorkerRuntimeDocker:

    def test__docker_run_args__shape(self):
        args = Worker__Runtime__Docker().docker_run_args(_spec())
        assert args[:6]                              == ['docker', 'run', '-d', '--rm', '--name', 'uj-w1']
        assert args[-1]                              == 'docker.io/sgraph/uj-worker:1.0'
        assert 'SG_UJ__RUN_ID=run-abc'               in args
        assert 'SG_UJ__WORKER_ID=w1'                 in args
        assert 'SG_UJ__JOURNEY_ID=checkout'          in args
        assert 'SG_UJ__ENVIRONMENT=prod'             in args

    def test__network_added_when_set(self):
        runtime         = Worker__Runtime__Docker()
        runtime.network = 'sg-net'
        args            = runtime.docker_run_args(_spec())
        assert '--network' in args
        assert 'sg-net'    in args

    def test__environment_omitted_when_absent(self):
        spec             = _spec()
        spec.environment = None
        args             = Worker__Runtime__Docker().docker_run_args(spec)
        assert not any(arg.startswith('SG_UJ__ENVIRONMENT=') for arg in args)

    def test__missing_image_raises_at_boundary(self):
        spec              = _spec()
        spec.worker_image = None
        with pytest.raises(ValueError):
            Worker__Runtime__Docker().docker_run_args(spec)

    def test__launch_runs_docker_and_returns_running(self):
        runtime = Recording__Docker()
        worker  = runtime.launch(_spec())
        assert worker.state          == Enum__Worker__State.RUNNING
        assert str(worker.worker_id) == 'w1'
        assert str(worker.run_id)    == 'run-abc'
        assert str(worker.container_name) == 'uj-w1'
        assert runtime.commands[0][:2]    == ['docker', 'run']

    def test__stop_removes_container_and_returns_stopped(self):
        runtime = Recording__Docker()
        worker  = runtime.launch(_spec())
        stopped = runtime.stop(worker)
        assert stopped.state       == Enum__Worker__State.STOPPED
        assert runtime.commands[-1] == ['docker', 'rm', '-f', 'uj-w1']

    def test__contract_matches_in_memory_naming(self):
        from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__InMemory import Worker__Runtime__InMemory
        spec = _spec()
        assert Worker__Runtime__Docker().container_name(spec) == Worker__Runtime__InMemory().launch(spec).container_name
