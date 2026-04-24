# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Lambda__Variant
# Distinguishes the two SP CLI Lambda functions baked from the SAME image:
#
#   • BASELINE — boots the baked code; no AGENTIC_APP_* env vars set.
#                Always-available rollback escape hatch when the S3 zip is
#                broken or the agentic boot path explodes.
#                Lambda name: sp-playwright-cli-baseline-{stage}
#
#   • AGENTIC  — boots via Agentic_Boot_Shim; AGENTIC_APP_* env vars pin a
#                specific S3 zip version that the shim downloads + extracts
#                + prepends to sys.path before importing Fast_API__SP__CLI.
#                Code-only deploys hot-swap by flipping AGENTIC_APP_VERSION.
#                Lambda name: sp-playwright-cli-{stage}
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lambda__Variant(str, Enum):
    BASELINE = 'baseline'
    AGENTIC  = 'agentic'

    def __str__(self):
        return self.value
