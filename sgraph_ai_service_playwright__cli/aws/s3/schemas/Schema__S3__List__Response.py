# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__S3__List__Response
# Result of a ListObjectsV2 call — objects + common prefix folders.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket     import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Next_Token import Safe_Str__S3__Next_Token
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Prefix     import Safe_Str__S3__Prefix
from sgraph_ai_service_playwright__cli.aws.s3.schemas.Schema__S3__Object          import Schema__S3__Object


class Schema__S3__List__Response(Type_Safe):
    bucket        : Safe_Str__S3__Bucket
    prefix        : Safe_Str__S3__Prefix
    objects       : list = None                                                     # list[Schema__S3__Object]
    prefixes      : list = None                                                     # list[str] — common prefixes (folders)
    truncated     : bool = False
    next_token    : Safe_Str__S3__Next_Token

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.objects  is None:
            self.objects  = []
        if self.prefixes is None:
            self.prefixes = []
