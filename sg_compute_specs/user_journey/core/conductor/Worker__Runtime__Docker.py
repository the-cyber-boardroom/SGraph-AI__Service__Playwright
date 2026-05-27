# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Worker__Runtime__Docker (real `docker run` launch port)
#
# The deploy-time sibling of Worker__Runtime__InMemory: launches each worker as a
# detached container from the spec's resolved image, injecting the run identity as
# SG_UJ__* env vars so the worker entrypoint can stamp X-SG-Run-Id. docker_run_args()
# is pure (argv only) so launch/stop are unit-testable by subclassing run_docker —
# the single subprocess seam — to record commands instead of touching the daemon.
# Everything above the port (Suite__Service) is identical to the in-memory backend.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import shutil
import subprocess

from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key import Safe_Str__Key

from sg_compute_specs.user_journey.core.conductor.Worker__Runtime              import Worker__Runtime
from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec import Schema__Worker__Spec
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State       import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status    import Schema__Worker__Status


def docker_available() -> bool:                                                     # binary present AND daemon reachable
    if shutil.which('docker') is None:
        return False
    try:
        return subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=10).returncode == 0
    except Exception:
        return False


class Worker__Runtime__Docker(Worker__Runtime):
    network : Safe_Str__Key = None                                                  # optional docker network to join

    def container_name(self, spec: Schema__Worker__Spec) -> str:
        return f'uj-{spec.worker_id}'                                               # identical to the in-memory backend

    def docker_run_args(self, spec: Schema__Worker__Spec) -> list:                  # pure: spec → `docker run` argv
        if spec.worker_image is None:                                               # boundary guard — never shell a 'None' image
            raise ValueError('worker_image is required to launch a worker container')
        args = ['docker', 'run', '-d', '--rm', '--name', self.container_name(spec)]
        if self.network is not None:
            args += ['--network', str(self.network)]
        args += ['-e', f'SG_UJ__RUN_ID={spec.run_id}',                              # entrypoint stamps this as X-SG-Run-Id
                 '-e', f'SG_UJ__WORKER_ID={spec.worker_id}',
                 '-e', f'SG_UJ__JOURNEY_ID={spec.journey_id}']
        if spec.environment is not None:
            args += ['-e', f'SG_UJ__ENVIRONMENT={spec.environment}']
        if spec.journey is not None:                                                # the worker loads this (no store, no callback)
            args += ['-e', f'SG_UJ__JOURNEY_JSON={json.dumps(spec.journey.json())}']
        args.append(str(spec.worker_image))
        return args

    def launch(self, spec: Schema__Worker__Spec) -> Schema__Worker__Status:
        self.run_docker(self.docker_run_args(spec))
        worker                = Schema__Worker__Status(state=Enum__Worker__State.RUNNING)
        worker.worker_id      = spec.worker_id
        worker.run_id         = spec.run_id
        worker.journey_id     = spec.journey_id
        worker.container_name = self.container_name(spec)
        return worker

    def stop(self, worker: Schema__Worker__Status) -> Schema__Worker__Status:
        if worker.container_name is not None:
            self.run_docker(['docker', 'rm', '-f', str(worker.container_name)], check=False)
        worker.state = Enum__Worker__State.STOPPED
        return worker

    def run_docker(self, cmd: list, check: bool = True):                            # the only subprocess seam (tests subclass this)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if check and proc.returncode != 0:
            raise RuntimeError(f'{" ".join(cmd[:3])} failed: {proc.stderr.strip()}')
        return proc
