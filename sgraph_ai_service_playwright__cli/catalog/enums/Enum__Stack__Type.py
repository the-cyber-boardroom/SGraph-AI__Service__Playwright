# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Stack__Type
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Stack__Type(Enum):
    DOCKER     = 'docker'
    PODMAN     = 'podman'
    ELASTIC    = 'elastic'
    OPENSEARCH = 'opensearch'
    PROMETHEUS = 'prometheus'
    VNC        = 'vnc'
    NEKO       = 'neko'
    FIREFOX    = 'firefox'
