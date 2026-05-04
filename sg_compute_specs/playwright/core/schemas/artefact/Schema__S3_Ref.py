# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__S3_Ref (spec §5.3)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id              import Safe_Str__Id

from sg_compute_specs.playwright.core.schemas.primitives.s3.Safe_Str__S3_Bucket                  import Safe_Str__S3_Bucket
from sg_compute_specs.playwright.core.schemas.primitives.s3.Safe_Str__S3_Key                     import Safe_Str__S3_Key


class Schema__S3_Ref(Type_Safe):                                                    # Points to an S3 object
    bucket  : Safe_Str__S3_Bucket
    key     : Safe_Str__S3_Key
    version : Safe_Str__Id = None                                                   # S3 object version ID if bucket versioned
