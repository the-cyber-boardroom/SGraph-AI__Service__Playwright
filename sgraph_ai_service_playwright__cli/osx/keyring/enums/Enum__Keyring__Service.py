# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Enum__Keyring__Service
# Fixed keyring service name prefixes used for all sg-managed secrets.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Keyring__Service(str, Enum):
    ROLE        = 'sg.config.role'     # sg.config.role.<name> — JSON role blob
    ROUTES      = 'sg.config.routes'   # sg.config.routes — JSON route list
    AWS_ROLE    = 'sg.aws'             # sg.aws.<role>.access_key / .secret_key
    VAULT       = 'sg.vault'           # sg.vault.<name>
    SECRET      = 'sg.secret'          # sg.secret.<ns>.<name>

    def __str__(self): return self.value
