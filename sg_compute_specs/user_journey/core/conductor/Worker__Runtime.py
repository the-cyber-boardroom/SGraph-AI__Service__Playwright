# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Worker__Runtime (the launch port)
#
# The seam between the suite lifecycle and how a worker container actually runs.
# Worker__Runtime__InMemory is the test/default backend; the Docker-socket backend
# (real `docker run`) is a sibling implementation added with the deploy harness.
# Keeping launch behind this port is what makes Suite__Service unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec import Schema__Worker__Spec
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status   import Schema__Worker__Status


class Worker__Runtime(Type_Safe):                                                   # abstract launch port

    def launch(self, spec: Schema__Worker__Spec) -> Schema__Worker__Status:
        raise NotImplementedError

    def stop(self, worker: Schema__Worker__Status) -> Schema__Worker__Status:
        raise NotImplementedError
