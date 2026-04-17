# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Get_Url (spec §5.7)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class Schema__Step__Result__Get_Url(Schema__Step__Result__Base):                    # Result from get_url
    url                 : Safe_Str__Url
