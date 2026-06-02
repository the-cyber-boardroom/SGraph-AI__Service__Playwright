# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Inspect__Request (Φ5 — probe-batch)
#
# Body for POST /inspect. Implements the "snapshot-once, probe-many" pattern
# from the @Content debrief addendum §4.1: one navigate + settle, then fan
# out a named bag of read-only probes against the same DOM state.
#
# Field semantics:
#   • navigate            — standard navigate step (url + wait_until + timeout_ms)
#   • settle              — list of wait_for-style step dicts (text / function
#                           / network_idle_ms / selector / state). Empty / None
#                           = skip the settle phase.
#   • probes              — Dict[name, step_dict]. Each value is a step dict
#                           that parses via STEP_SCHEMAS — restricted at execution
#                           time to read-only verbs (get_url, get_text, get_html,
#                           get_dom_tree, get_a11y_tree, screenshot,
#                           get_console_tail, get_network_failures). The name
#                           is caller-chosen and carries through to the response.
#   • diagnostics_on_fail — when True (default), if ANY step failed the response
#                           carries a `diagnostics` block (console + network
#                           failures). Cheap insurance; defaults on.
#   • browser_config /
#     capture_config /
#     credentials /
#     timeout_ms          — same shape as Schema__Sequence__Request.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS                  import Safe_UInt__Timeout_MS
from sg_compute_specs.playwright.core.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Navigate                              import Schema__Step__Navigate


class Schema__Inspect__Request(Type_Safe):                                          # POST /inspect body
    navigate            : Schema__Step__Navigate                                    # The one navigate that anchors the snapshot
    settle              : List[dict]                                                # Wait-for-style steps; empty list = skip settle
    probes              : Dict[str, dict]                                           # name → probe step dict (read-only verbs only)
    diagnostics_on_fail : bool                          = True                      # Default on — diagnostics are cheap, ~few KB
    browser_config      : Schema__Browser__Config       = None
    capture_config      : Schema__Capture__Config       = None
    credentials         : Schema__Session__Credentials  = None
    timeout_ms          : Safe_UInt__Timeout_MS         = None
    trace_id            : Safe_Str__Trace_Id            = None
