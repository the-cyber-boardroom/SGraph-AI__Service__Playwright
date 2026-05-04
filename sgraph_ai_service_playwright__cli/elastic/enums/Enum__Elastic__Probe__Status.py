# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Elastic__Probe__Status
# Classifies one HTTP probe of a stack's Elasticsearch endpoint (via the nginx
# /_elastic/ rewrite). Lets `sp elastic wait` show "ES ready" before "Kibana
# ready" — the typical Elastic boot order is ES (~30s) → token mint → Kibana
# (~60-90s), and seed/index work can begin as soon as ES is green.
#
#   UNREACHABLE   — connection refused / DNS fail / timeout before any response
#   AUTH_REQUIRED — ES answered 401/403 (creds missing or wrong)
#   RED           — _cluster/health returned status=red (unallocated shards)
#   YELLOW        — _cluster/health returned status=yellow (single-node, normal)
#   GREEN         — _cluster/health returned status=green (all shards assigned)
#   UNKNOWN       — any other response we don't model
#
# READY = YELLOW or GREEN. On a single-node cluster yellow is the resting
# state because replicas have nowhere to go — yellow still accepts writes.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Elastic__Probe__Status(str, Enum):
    UNREACHABLE   = 'unreachable'
    AUTH_REQUIRED = 'auth-required'
    RED           = 'red'
    YELLOW        = 'yellow'
    GREEN         = 'green'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value

    def is_ready(self) -> bool:
        return self in (Enum__Elastic__Probe__Status.YELLOW, Enum__Elastic__Probe__Status.GREEN)
