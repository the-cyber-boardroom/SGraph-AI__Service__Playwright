# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Worker__Runtime__InMemory
#
# Default/test backend: records the launched specs and returns a RUNNING worker
# status without touching Docker. The conductor swaps in the Docker-socket backend
# at deploy time; everything above the port (Suite__Service) is identical.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from sg_compute_specs.user_journey.core.conductor.Worker__Runtime              import Worker__Runtime
from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec import Schema__Worker__Spec
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State       import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status    import Schema__Worker__Status


class Worker__Runtime__InMemory(Worker__Runtime):
    launched : List[Schema__Worker__Spec]                                           # specs this runtime was asked to launch

    def launch(self, spec: Schema__Worker__Spec) -> Schema__Worker__Status:
        self.launched.append(spec)
        worker                = Schema__Worker__Status(state=Enum__Worker__State.RUNNING)
        worker.worker_id      = spec.worker_id
        worker.run_id         = spec.run_id
        worker.journey_id     = spec.journey_id
        worker.container_name = f'uj-{spec.worker_id}'
        return worker

    def stop(self, worker: Schema__Worker__Status) -> Schema__Worker__Status:
        worker.state = Enum__Worker__State.STOPPED
        return worker
