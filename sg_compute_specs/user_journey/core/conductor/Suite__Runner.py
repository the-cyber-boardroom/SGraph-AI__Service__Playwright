# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Suite__Runner (the fan-out planner)
#
# Pure scheduling logic: expand a Schema__Suite__Definition into per-replica worker
# specs and chunk them into launch waves of `concurrency` (load = count). The actual
# `docker run` is delegated to a runtime port (a later sub-slice) — this class only
# decides what to launch and in what order, so it is fully unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.user_journey.core.schemas.conductor.Schema__Worker__Spec                          import Schema__Worker__Spec


class Suite__Runner(Type_Safe):                                                     # decides what to launch, in what order

    def expand_entry(self, entry, default_image=None, journeys=None) -> List[Schema__Worker__Spec]:
        image   = entry.worker_image if entry.worker_image is not None else default_image
        journey = str(entry.journey_id) if entry.journey_id is not None else 'journey'
        defn    = journeys.get(journey) if (journeys and entry.journey_id is not None) else None
        specs   = []
        for replica in range(int(entry.count)):
            spec               = Schema__Worker__Spec(replica_index=replica)
            worker_id          = f'{journey}-{replica:05d}'
            spec.worker_id     = worker_id
            spec.run_id        = worker_id                                          # unique within the plan; stamped as X-SG-Run-Id
            if image              is not None: spec.worker_image = image
            if entry.journey_id   is not None: spec.journey_id   = entry.journey_id
            if entry.environment  is not None: spec.environment  = entry.environment
            if defn               is not None: spec.journey       = defn            # carried into SG_UJ__JOURNEY_JSON
            specs.append(spec)
        return specs

    def chunk(self, specs: List, size) -> List[List]:
        size = max(1, int(size))
        return [specs[index:index + size] for index in range(0, len(specs), size)]

    def waves_for_entry(self, entry, default_image=None, journeys=None) -> List[List[Schema__Worker__Spec]]:
        return self.chunk(self.expand_entry(entry, default_image, journeys), int(entry.concurrency))

    def plan(self, suite_definition, default_image=None, journeys=None) -> List[List[Schema__Worker__Spec]]:
        waves = []
        for entry in suite_definition.entries:                                      # entries run in order; each chunked by its concurrency
            waves.extend(self.waves_for_entry(entry, default_image, journeys))
        return waves
