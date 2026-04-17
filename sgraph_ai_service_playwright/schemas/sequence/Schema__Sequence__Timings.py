# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Timings
#
# Wall-clock breakdown of a single stateless sequence execution. Each field is
# populated by Sequence__Runner as the phases complete, and the result is
# surfaced in Schema__Sequence__Response.timings — and reused by the Quick
# response schemas and the /quick/screenshot raw-PNG endpoint (via HTTP
# response headers).
#
# Intent: a caller can tell at a glance where the latency went (did Chromium
# boot slow? did the page take forever? did teardown stall?) without having
# to instrument their own stopwatch.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds     import Safe_UInt__Milliseconds


class Schema__Sequence__Timings(Type_Safe):
    playwright_start_ms  : Safe_UInt__Milliseconds                                   # sync_playwright().start() — Node subprocess boot
    browser_launch_ms    : Safe_UInt__Milliseconds                                   # chromium.launch() — browser process boot
    steps_ms             : Safe_UInt__Milliseconds                                   # Wall clock across step execution (navigate + click + capture etc.)
    browser_close_ms     : Safe_UInt__Milliseconds                                   # browser.close() + playwright.stop() — teardown
    total_ms             : Safe_UInt__Milliseconds                                   # Outer wall clock; always >= sum of the others (includes glue time)
