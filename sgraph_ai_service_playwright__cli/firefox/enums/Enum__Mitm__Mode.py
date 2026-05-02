# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Mitm__Mode
# Operating mode of the mitmproxy sidecar on the Firefox stack.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Mitm__Mode(str, Enum):
    INTERCEPT   = 'intercept'    # traffic is inspected and optionally modified
    PASSTHROUGH = 'passthrough'  # traffic flows through without modification
