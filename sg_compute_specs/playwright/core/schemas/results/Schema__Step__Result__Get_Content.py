# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Get_Content (spec §5.7)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Content_Type            import Safe_Str__Http__Content_Type

from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                               import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Page__Content                   import Safe_Str__Page__Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class Schema__Step__Result__Get_Content(Schema__Step__Result__Base):                # Result from get_content
    content             : Safe_Str__Page__Content                                   # Up to 10 MB HTML/text — real pages routinely exceed the 64 KB Safe_Str__Text__Dangerous cap
    content_format      : Enum__Content__Format
    content_type        : Safe_Str__Http__Content_Type = "text/html"
