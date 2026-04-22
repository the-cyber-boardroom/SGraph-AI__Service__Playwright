# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Screenshot__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                           import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id               import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds               import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Page__Content                  import Safe_Str__Page__Content


class Schema__Screenshot__Response(Type_Safe):
    url             : Safe_Str__Url           = None
    screenshot_b64  : str                     = None                                # base64-encoded PNG; None when format=html
    html            : Safe_Str__Page__Content = None                                # rendered HTML; None when format=png
    duration_ms     : Safe_UInt__Milliseconds = Safe_UInt__Milliseconds(0)
    trace_id        : Safe_Str__Trace_Id      = None
