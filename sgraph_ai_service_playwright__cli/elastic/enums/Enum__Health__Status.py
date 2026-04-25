# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Health__Status
# Status of one row in `sp elastic health`. Four levels so a single failed
# check doesn't dominate the table — WARN is for "the answer was unexpected
# but we got an answer" (e.g. SG ingress allows a different IP than current).
#
#   OK   — check passed
#   WARN — degraded but not blocking (e.g. ES yellow on single-node is normal)
#   FAIL — blocking; something is wrong and the user needs to act
#   SKIP — check was not run (e.g. SSM probes when --no-ssm passed, or the
#          instance has no public IP yet)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Health__Status(str, Enum):
    OK   = 'ok'
    WARN = 'warn'
    FAIL = 'fail'
    SKIP = 'skip'

    def __str__(self):
        return self.value
