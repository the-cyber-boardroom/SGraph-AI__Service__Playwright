# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Vault__Source
# One vault to load onto the box at build/deploy (post-MVP). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Vault__Kind          import Enum__Content_Proxy__Vault__Kind
from sg_compute_specs.content_proxy.primitives.Safe_Str__Content_Proxy__Ref         import Safe_Str__Content_Proxy__Ref


class Schema__Content_Proxy__Vault__Source(Type_Safe):
    kind   : Enum__Content_Proxy__Vault__Kind = Enum__Content_Proxy__Vault__Kind.ZIP
    ref    : Safe_Str__Content_Proxy__Ref                                            # local zip path, or sgit/s3 ref for SGIT
    target : Safe_Str__Text                                                          # vault name/slot inside the vault app
