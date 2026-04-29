# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Stack__Type
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Type(Enum):
    LINUX      = 'linux'
    DOCKER     = 'docker'
    ELASTIC    = 'elastic'
    OPENSEARCH = 'opensearch'
    PROMETHEUS = 'prometheus'
    VNC        = 'vnc'
    NEKO       = 'neko'
