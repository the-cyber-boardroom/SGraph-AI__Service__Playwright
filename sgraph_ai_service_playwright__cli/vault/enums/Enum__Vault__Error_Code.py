# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Vault__Error_Code
# Typed error codes returned in vault 4xx responses.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault__Error_Code(str, Enum):
    NO_VAULT_ATTACHED    = 'no-vault-attached'    # 409 — service has no vault token
    UNKNOWN_PLUGIN       = 'unknown-plugin'        # 400 — plugin_id not in catalog
    DISALLOWED_HANDLE    = 'disallowed-handle'     # 400 — handle not in plugin.write_handles
    PAYLOAD_TOO_LARGE    = 'payload-too-large'     # 413 — blob exceeds per-plugin size cap
