# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Prom__Stack__State
# Lifecycle state for an ephemeral Prometheus stack. READY means Prometheus
# is answering on its public port — the EC2 instance can be RUNNING but
# Prometheus still booting. Mirrors Enum__OS__Stack__State /
# Enum__Elastic__State so all sister sections share the same vocabulary.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Prom__Stack__State(str, Enum):
    PENDING      = 'pending'                                                        # EC2 run_instances accepted, instance not yet running
    RUNNING      = 'running'                                                        # EC2 running; Prometheus may still be booting
    READY        = 'ready'                                                          # Prometheus /-/healthy responds 200
    TERMINATING  = 'terminating'                                                    # Terminate initiated; EC2 shutting-down
    TERMINATED   = 'terminated'                                                     # EC2 terminated
    UNKNOWN      = 'unknown'                                                        # Anything AWS returns we don't model

    def __str__(self):
        return self.value
