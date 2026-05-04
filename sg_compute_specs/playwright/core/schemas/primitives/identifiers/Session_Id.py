# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Session_Id primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.identifiers.Safe_Id import Safe_Id


class Session_Id(Safe_Id):                                                          # Browser session handle (auto-generates)
    pass                                                                            # Inherits Safe_Id auto-gen behaviour
