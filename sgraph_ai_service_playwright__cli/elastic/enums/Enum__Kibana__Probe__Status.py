# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Kibana__Probe__Status
# Classifies one HTTP probe of a stack's Kibana endpoint during `sp elastic
# wait`. Lets the CLI render a useful per-tick status instead of just a spinner.
#
#   UNREACHABLE   — connection refused / DNS fail / timeout before any response
#   UPSTREAM_DOWN — nginx responded 5xx (typically 502: Kibana container not
#                   up yet; 503: Kibana booting but not green yet)
#   BOOTING       — Kibana answered /api/status but not 200 (rare intermediate)
#   READY         — /api/status returned HTTP 200 — Kibana is serving
#   UNKNOWN       — any other response we don't model
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Kibana__Probe__Status(str, Enum):
    UNREACHABLE   = 'unreachable'
    UPSTREAM_DOWN = 'upstream-down'
    BOOTING       = 'booting'
    READY         = 'ready'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value
