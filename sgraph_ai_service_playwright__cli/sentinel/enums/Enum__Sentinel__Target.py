# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Sentinel__Target
# The three execution targets the signal spine must be byte-identical across.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Sentinel__Target(str, Enum):
    LOCAL_DIRECT = 'local-direct'
    LOCAL_DOCKER = 'local-docker'
    AWS          = 'aws'
