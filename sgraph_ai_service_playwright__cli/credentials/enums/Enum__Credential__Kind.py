# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Enum__Credential__Kind
# Discriminator for the type of credential stored in the keyring.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Credential__Kind(str, Enum):
    ROLE    = 'role'    # sg.config.role.<name>   — JSON role config blob
    AWS     = 'aws'     # sg.aws.<role>.access_key / .secret_key
    VAULT   = 'vault'   # sg.vault.<name>
    SECRET  = 'secret'  # sg.secret.<ns>.<name>
    ROUTES  = 'routes'  # sg.config.routes — JSON route list

    def __str__(self): return self.value
