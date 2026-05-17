# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Enum__Audit__Action
# Actions recorded in the JSONL audit log.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Audit__Action(str, Enum):
    ADD      = 'add'
    REMOVE   = 'remove'
    SWITCH   = 'switch'
    EDIT     = 'edit'
    EXPORT   = 'export'
    ASSUME   = 'assume'
    LIST     = 'list'
    SHOW     = 'show'
    STATUS   = 'status'

    def __str__(self): return self.value
