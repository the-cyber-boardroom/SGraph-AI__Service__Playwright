# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Vault__Kind
# How a vault is loaded onto the box at build/deploy (post-MVP).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Vault__Kind(str, Enum):
    ZIP  = 'zip'                                                                    # a bundled vault archive copied in
    SGIT = 'sgit'                                                                   # sgit clone from a live server or an s3:// bucket
