# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Proxy__Tool
# Which mitmproxy binary the proxy containers run.
#   MITMWEB  — has the /flows web API the TUI reads. Accumulates flows IN MEMORY,
#              so it is a DEV/QA choice; long prod runs grow unbounded.
#   MITMDUMP — headless, no flow accumulation. The PROD-safe choice (no TUI flows).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Proxy__Tool(str, Enum):
    MITMWEB  = 'mitmweb'                                                            # dev/QA — TUI /flows, in-memory accumulation
    MITMDUMP = 'mitmdump'                                                           # prod   — headless, no accumulation
