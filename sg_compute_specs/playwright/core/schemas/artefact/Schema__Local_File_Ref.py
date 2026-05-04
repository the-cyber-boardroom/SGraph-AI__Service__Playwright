# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Local_File_Ref (spec §5.3)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path                import Safe_Str__File__Path


class Schema__Local_File_Ref(Type_Safe):                                            # Points to a local filesystem path
    path : Safe_Str__File__Path                                                     # Rejected on Lambda / Claude Web
