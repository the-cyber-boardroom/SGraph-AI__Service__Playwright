# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Get_Url (spec §5.7)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class Schema__Step__Result__Get_Url(Schema__Step__Result__Base):                    # Result from get_url
    url                 : Safe_Str__Url
