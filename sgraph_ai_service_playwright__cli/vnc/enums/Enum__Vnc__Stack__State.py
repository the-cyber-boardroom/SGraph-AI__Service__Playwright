# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Vnc__Stack__State
# Lifecycle state for an ephemeral browser-viewer stack. READY means nginx is
# answering 200 + mitmweb is reachable — the EC2 instance can be RUNNING but
# the chromium container still booting. Mirrors the other sister sections so
# all share the same vocabulary.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vnc__Stack__State(str, Enum):
    PENDING      = 'pending'                                                        # EC2 run_instances accepted, instance not yet running
    RUNNING      = 'running'                                                        # EC2 running; nginx / chromium / mitmproxy may still be booting
    READY        = 'ready'                                                          # nginx 200 + mitmweb /api/flows reachable
    TERMINATING  = 'terminating'                                                    # Terminate initiated; EC2 shutting-down
    TERMINATED   = 'terminated'                                                     # EC2 terminated
    UNKNOWN      = 'unknown'                                                        # Anything AWS returns we don't model

    def __str__(self):
        return self.value
