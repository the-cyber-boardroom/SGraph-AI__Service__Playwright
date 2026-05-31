# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Get_Url (spec §5.7)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class Schema__Step__Result__Get_Url(Schema__Step__Result__Base):                    # Result from get_url
    url                 : Safe_Str__Url__Permissive                                 # Permissive: page.url may legitimately contain ':' in fragment (vault keys, etc.) — see BUG-1 in the 05-30 debrief response pack
