# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Instance__State
# Lifecycle state of a per-slug vault EC2 instance.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Instance__State(str, Enum):
    STOPPED  = 'stopped'      # not running — a cold request triggers the wake sequence
    PENDING  = 'pending'      # start requested, not yet healthy
    RUNNING  = 'running'      # healthy and serving
    STOPPING = 'stopping'     # idle-shutdown in progress
    UNKNOWN  = 'unknown'      # no instance allocated for the slug yet
