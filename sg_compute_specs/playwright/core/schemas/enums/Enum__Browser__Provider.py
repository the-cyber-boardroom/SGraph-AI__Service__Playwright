# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Browser__Provider
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Browser__Provider(str, Enum):                                           # How the browser is obtained
    LOCAL_SUBPROCESS = "local_subprocess"                                           # Spawn chromium process in this container
    CDP_CONNECT      = "cdp_connect"                                                # Connect via CDP to a pre-existing browser
    BROWSERLESS      = "browserless"                                                # Cloud provider (browserless.io)

    def __str__(self): return self.value
