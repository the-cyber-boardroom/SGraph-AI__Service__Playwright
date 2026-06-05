# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Enum__Vault_App__Interceptor__Kind
# How the agent-mitmproxy interceptor source is supplied at create time.
#   none   — no interceptor (a no-op script is written so mitmdump --scripts resolves)
#   inline — raw Python source (the CLI reads --interceptor-script <file> into this)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_App__Interceptor__Kind(str, Enum):
    NONE   = 'none'
    INLINE = 'inline'

    def __str__(self):
        return self.value
