# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Screenshot__Batch__Request
#
# Two modes (discriminated by which list is populated):
#   items — N independent screenshots, each in its own browser session.
#   steps — single browser session; each step navigates + optionally JS/click.
#           screenshot_per_step=True captures after every step;
#           screenshot_per_step=False captures only after the last step.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                        import List

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe

from sgraph_ai_service_playwright.schemas.screenshot.Schema__Screenshot__Request                   import Schema__Screenshot__Request


class Schema__Screenshot__Batch__Request(Type_Safe):
    items               : List[Schema__Screenshot__Request]                          # Form 1: independent browser sessions
    steps               : List[Schema__Screenshot__Request]                          # Form 2: sequential steps in one session
    screenshot_per_step : bool                              = False                 # Form 2 only: capture after each step
