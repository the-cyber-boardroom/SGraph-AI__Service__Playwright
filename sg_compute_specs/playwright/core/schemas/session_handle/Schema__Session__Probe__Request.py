# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Probe__Request (Φ7)
#
# Body for POST /session/{id}/probe. Same shape as Schema__Inspect__Request
# minus the `navigate` field (the held page is already at some URL) and
# minus browser_config / credentials (locked in at /session/open). The
# probes run against the held page in its CURRENT state.
#
# Typical use: open session → /act with navigate + decrypt → multiple
# /probe calls extract different facets of the same DOM without redoing
# the expensive navigate.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id


class Schema__Session__Probe__Request(Type_Safe):                                   # POST /session/{id}/probe body
    settle              : List[dict]                                                # Optional settle steps before probing; empty list = skip
    probes              : Dict[str, dict]                                           # name → read-only probe step dict (same allowlist as /inspect)
    diagnostics_on_fail : bool                          = True
    capture_config      : Schema__Capture__Config       = None
    trace_id            : Safe_Str__Trace_Id            = None
