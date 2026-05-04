# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__OS__Stack__State
# Lifecycle state for an ephemeral OpenSearch + Dashboards stack. Distinct
# from Enum__Instance__State because READY means OpenSearch Dashboards is
# actually answering on its public port — the EC2 instance can be RUNNING
# but Dashboards still booting.
#
# Mirrors Enum__Elastic__State; both sister sections share this lifecycle
# vocabulary so callers can swap between sp el and sp os with the same
# state-handling code.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__OS__Stack__State(str, Enum):
    PENDING      = 'pending'                                                        # EC2 run_instances accepted, instance not yet running
    RUNNING      = 'running'                                                        # EC2 running; Dashboards may still be booting
    READY        = 'ready'                                                          # OpenSearch Dashboards responds 200 on the health probe
    TERMINATING  = 'terminating'                                                    # Terminate initiated; EC2 shutting-down
    TERMINATED   = 'terminated'                                                     # EC2 terminated
    UNKNOWN      = 'unknown'                                                        # Anything AWS returns we don't model

    def __str__(self):
        return self.value
