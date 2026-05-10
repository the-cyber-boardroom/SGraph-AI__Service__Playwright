# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Defaults
# One source of truth for CLI defaults shared by every spec.
# ═══════════════════════════════════════════════════════════════════════════════

import os

DEFAULT_REGION         = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_MAX_HOURS      = 1.0          # D2 — every spec defaults to 1h auto-shutdown; float allows 0.1 = 6 min
DEFAULT_TIMEOUT_SEC    = 600
DEFAULT_POLL_SEC       = 10
DEFAULT_EXEC_TIMEOUT   = 60
