# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Slug__Validator
# Pure-validation class: returns the first failing Enum__Slug__Error_Code or
# None on success. Callers (Slug__Registry) wire in the reserved-set check.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Enum__Slug__Error_Code      import Enum__Slug__Error_Code
from sg_compute_specs.vault_publish.service.reserved.Reserved__Slugs    import RESERVED_SLUGS

_VALID_CHARSET = re.compile(r'^[a-z0-9-]+$')


class Slug__Validator(Type_Safe):

    def validate(self, slug: str) -> 'Enum__Slug__Error_Code | None':
        if not slug:
            return Enum__Slug__Error_Code.EMPTY
        if not _VALID_CHARSET.match(slug):
            return Enum__Slug__Error_Code.INVALID_CHARSET
        if len(slug) > 63:
            return Enum__Slug__Error_Code.TOO_LONG
        if slug.startswith('-'):
            return Enum__Slug__Error_Code.LEADING_HYPHEN
        if slug.endswith('-'):
            return Enum__Slug__Error_Code.TRAILING_HYPHEN
        if '--' in slug:
            return Enum__Slug__Error_Code.CONSECUTIVE_HYPHENS
        if slug in RESERVED_SLUGS:
            return Enum__Slug__Error_Code.RESERVED
        return None
