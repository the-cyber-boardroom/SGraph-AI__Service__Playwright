# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Enum__Slug__Error_Code
# Closed set of validation failure reasons returned by Slug__Validator.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Slug__Error_Code(str, Enum):
    INVALID_CHARSET       = 'invalid-charset'
    TOO_LONG              = 'too-long'
    LEADING_HYPHEN        = 'leading-hyphen'
    TRAILING_HYPHEN       = 'trailing-hyphen'
    CONSECUTIVE_HYPHENS   = 'consecutive-hyphens'
    RESERVED              = 'reserved'
    ALREADY_REGISTERED    = 'already-registered'
    EMPTY                 = 'empty'

    def __str__(self):
        return self.value
