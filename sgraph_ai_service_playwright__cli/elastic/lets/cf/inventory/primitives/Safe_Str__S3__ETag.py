# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__ETag
# S3 ETag, normalised to no surrounding quotes. Two valid shapes:
#   1. 32 hex chars            — single-part upload (md5 of the object body)
#   2. 32 hex chars + "-N"     — multipart upload (N is the part count)
# Firehose-emitted CloudFront log objects are always single-part because
# they're well under the 5 MB multipart threshold. We accept both shapes so
# the type works for any future LETS source.
# Used as the Elastic _id so re-loads dedupe at index time.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__ETag(Safe_Str):
    regex             = re.compile(r'^[a-f0-9]{32}(-\d{1,5})?$')                     # md5 hex with optional "-N" multipart marker
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 64
    allow_empty       = True                                                        # Auto-init support; service rejects empty on persist
    to_lower_case     = True                                                        # AWS returns lowercase hex; normalise just in case
    trim_whitespace   = True
