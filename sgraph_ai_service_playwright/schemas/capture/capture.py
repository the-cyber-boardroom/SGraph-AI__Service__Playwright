# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Capture Configuration (spec §5.4)
#
# Validation is per-action. The capture_config is registered at session creation
# or sequence submission, but each individual step that triggers a capture re-
# validates the relevant sink against current deployment capabilities.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe

from sgraph_ai_service_playwright.schemas.artefact.artefact                                       import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.enums.enums                                             import Enum__Video__Codec


class Schema__Capture__Config(Type_Safe):                                           # What to capture + where to put it
    # ── Per-artefact sink config ───────────────────────────────────────────────
    screenshot              : Schema__Artefact__Sink_Config                         # Per-step screenshot
    screenshot_on_fail      : Schema__Artefact__Sink_Config                         # Only on step failure
    video                   : Schema__Artefact__Sink_Config                         # Full session recording
    pdf                     : Schema__Artefact__Sink_Config                         # PDF export of final page
    har                     : Schema__Artefact__Sink_Config                         # HTTP Archive
    trace                   : Schema__Artefact__Sink_Config                         # Playwright trace zip
    console_log             : Schema__Artefact__Sink_Config                         # Browser console
    network_log             : Schema__Artefact__Sink_Config                         # All HTTP requests
    page_content            : Schema__Artefact__Sink_Config                         # HTML snapshot at end

    # ── Response-shape flags (always inline) ──────────────────────────────────
    include_execution_result : bool = True                                          # pass/fail + error messages
    include_performance_data : bool = True                                          # per-step timing
    include_prometheus       : bool = False                                         # Prometheus exposition format

    # ── Video-specific ────────────────────────────────────────────────────────
    video_codec              : Enum__Video__Codec = Enum__Video__Codec.WEBM
    video_viewport_only      : bool = True                                          # False captures full desktop (N/A headless)
