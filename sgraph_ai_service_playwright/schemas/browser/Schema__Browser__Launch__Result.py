# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Launch__Result
#
# Return shape of Browser__Launcher.launch(). Bundles the opaque Playwright
# objects (browser + sync_playwright runtime) with the two timings a stateless
# caller cares about: how long the Node subprocess took to boot, and how long
# Chromium took to launch.
#
# `browser` and `playwright` are typed as `Any` because the rest of the service
# treats them as opaque — only Browser__Launcher, Step__Executor, and the
# Runner's get_or_create_page ever reach into them directly.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                              import Any

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright.schemas.browser.Schema__Proxy__Config                  import Schema__Proxy__Config
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds     import Safe_UInt__Milliseconds


class Schema__Browser__Launch__Result(Type_Safe):
    browser              : Any                                                       # Playwright Browser handle
    playwright           : Any                                                       # sync_playwright() runtime (Node subprocess) — stopped in Browser__Launcher.stop()
    playwright_start_ms  : Safe_UInt__Milliseconds                                   # sync_playwright().start() duration
    browser_launch_ms    : Safe_UInt__Milliseconds                                   # chromium.launch() duration
    proxy                : Schema__Proxy__Config = None                              # Retained from browser_config so get_or_create_page can apply ignore_https_errors + bind CDP auth
