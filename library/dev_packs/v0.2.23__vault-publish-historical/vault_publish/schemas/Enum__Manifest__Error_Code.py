# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Manifest__Error_Code
# Reasons Manifest__Interpreter refuses a provisioning manifest. The interpreter
# is the allowlist boundary — it rejects, it never falls through to "just run it".
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Manifest__Error_Code(str, Enum):
    UNSUPPORTED_APP_TYPE = 'unsupported-app-type'   # app_type not in the allowlist
    UNSUPPORTED_RUNTIME  = 'unsupported-runtime'    # runtime not in the allowlist
    INCOMPATIBLE_RUNTIME = 'incompatible-runtime'   # runtime / app_type combination not allowed
    MISSING_CONTENT_ROOT = 'missing-content-root'   # content_root is empty
    MISSING_HEALTH_PATH  = 'missing-health-path'    # health_path is empty
