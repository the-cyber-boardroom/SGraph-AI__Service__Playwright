# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Vault__Error_Code
# Typed error codes returned in vault 4xx responses.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault__Error_Code(str, Enum):
    NO_VAULT_ATTACHED = 'no-vault-attached'   # 409 — service has no vault token
    UNKNOWN_SPEC      = 'unknown-spec'         # 400 — spec_id not in registry
    DISALLOWED_HANDLE = 'disallowed-handle'    # 400 — handle not in spec write_handles
    PAYLOAD_TOO_LARGE = 'payload-too-large'    # 413 — blob exceeds size cap
