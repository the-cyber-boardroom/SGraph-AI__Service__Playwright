# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Request (v0.1.24)
#
# Stateless multi-step execution request. `browser_config` is optional —
# defaults applied when omitted — and every call launches a fresh Chromium
# process that is torn down after the run. No session handles on the wire.
#
# `steps` is List[dict] on the wire; the Sequence__Dispatcher parses each
# entry via STEP_SCHEMAS (§8) based on the `action` discriminator.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Config                         import Schema__Sequence__Config
from sg_compute_specs.playwright.core.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials


class Schema__Sequence__Request(Type_Safe):                                         # POST /sequence/execute body
    sequence_id     : Sequence_Id              = None                               # Auto-generated if omitted
    browser_config  : Schema__Browser__Config  = None                               # Optional — defaults applied when omitted
    credentials     : Schema__Session__Credentials = None                           # Vault-glue (cookies / storage state / headers) applied to the fresh context
    capture_config  : Schema__Capture__Config
    sequence_config : Schema__Sequence__Config
    steps           : List[dict]                                                    # Heterogeneous; parsed by dispatcher via STEP_SCHEMAS
    trace_id        : Safe_Str__Trace_Id       = None
