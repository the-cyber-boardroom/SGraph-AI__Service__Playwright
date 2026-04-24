# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Elastic__State
# Lifecycle state for an ephemeral Elastic+Kibana stack. Distinct from
# Enum__Instance__State because "READY" means Kibana is actually answering on
# port 443 — the EC2 instance can be RUNNING but Kibana still starting.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Elastic__State(str, Enum):
    PENDING      = 'pending'                                                        # EC2 run_instances accepted, instance not yet running
    RUNNING      = 'running'                                                        # EC2 running; Kibana may still be booting
    READY        = 'ready'                                                          # Kibana responds 200 on the health probe
    TERMINATING  = 'terminating'                                                    # Terminate initiated; EC2 shutting-down
    TERMINATED   = 'terminated'                                                     # EC2 terminated
    UNKNOWN      = 'unknown'                                                        # Anything AWS returns we don't model

    def __str__(self):
        return self.value
