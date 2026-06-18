# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Proxy
# Which of the two mitmproxy instances a flow / request went through.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Proxy(str, Enum):
    EXT = 'ext'                                                                     # mitmproxy-ext :8080 — basic auth, for human browsers
    INT = 'int'                                                                     # mitmproxy-int :8081 — no auth, for the sg-playwright browser
