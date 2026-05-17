# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Slug__Validator
# The single place slug naming policy is decided. validate() returns a specific
# Enum__Slug__Error_Code (never a generic "invalid") or None when the slug is
# acceptable. to_slug() promotes a validated raw string to a typed Safe_Str__Slug.
#
# Rules: 3–40 chars; lowercase letters / digits / hyphens only; no leading,
# trailing or double hyphen; not reserved; not caught by the profanity filter.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from typing                                                  import Optional

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Enum__Slug__Error_Code            import Enum__Slug__Error_Code
from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.service.reserved.Reserved__Slugs          import Reserved__Slugs

SLUG_MIN_LENGTH = 3
SLUG_MAX_LENGTH = 40
_CHARSET_RE     = re.compile(r'^[a-z0-9\-]+$')

MESSAGE_FOR_ERROR = {
    Enum__Slug__Error_Code.TOO_SHORT       : 'slug must be at least 3 characters',
    Enum__Slug__Error_Code.TOO_LONG        : 'slug must be at most 40 characters',
    Enum__Slug__Error_Code.BAD_CHARSET     : 'slug may only contain lowercase letters, digits and hyphens',
    Enum__Slug__Error_Code.LEADING_HYPHEN  : 'slug must not start with a hyphen',
    Enum__Slug__Error_Code.TRAILING_HYPHEN : 'slug must not end with a hyphen',
    Enum__Slug__Error_Code.DOUBLE_HYPHEN   : 'slug must not contain a double hyphen',
    Enum__Slug__Error_Code.RESERVED        : 'slug is reserved and cannot be registered',
    Enum__Slug__Error_Code.PROFANE         : 'slug was rejected by the profanity filter',
}


class Slug__Validator(Type_Safe):
    reserved : Reserved__Slugs

    def validate(self, raw: str) -> Optional[Enum__Slug__Error_Code]:
        raw = str(raw)
        if len(raw) < SLUG_MIN_LENGTH        : return Enum__Slug__Error_Code.TOO_SHORT
        if len(raw) > SLUG_MAX_LENGTH        : return Enum__Slug__Error_Code.TOO_LONG
        if not _CHARSET_RE.match(raw)        : return Enum__Slug__Error_Code.BAD_CHARSET
        if raw.startswith('-')               : return Enum__Slug__Error_Code.LEADING_HYPHEN
        if raw.endswith('-')                 : return Enum__Slug__Error_Code.TRAILING_HYPHEN
        if '--' in raw                       : return Enum__Slug__Error_Code.DOUBLE_HYPHEN
        if self.reserved.is_reserved(raw)    : return Enum__Slug__Error_Code.RESERVED
        if self.reserved.is_profane(raw)     : return Enum__Slug__Error_Code.PROFANE
        return None

    def is_valid(self, raw: str) -> bool:
        return self.validate(raw) is None

    def message_for(self, error_code: Enum__Slug__Error_Code) -> str:
        return MESSAGE_FOR_ERROR.get(error_code, 'invalid slug')

    def to_slug(self, raw: str) -> Safe_Str__Slug:                           # caller must validate first
        error_code = self.validate(raw)
        if error_code is not None:
            raise ValueError(self.message_for(error_code))
        return Safe_Str__Slug(str(raw))
