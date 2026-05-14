# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Slug__Error_Code
# Specific reasons a slug fails Slug__Validator. Each maps to a clear, specific
# user-facing message — never a generic "invalid slug".
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Slug__Error_Code(str, Enum):
    TOO_SHORT       = 'too-short'         # fewer than 3 characters
    TOO_LONG        = 'too-long'          # more than 40 characters
    BAD_CHARSET     = 'bad-charset'       # characters outside lowercase / digits / hyphen
    LEADING_HYPHEN  = 'leading-hyphen'    # starts with a hyphen
    TRAILING_HYPHEN = 'trailing-hyphen'   # ends with a hyphen
    DOUBLE_HYPHEN   = 'double-hyphen'     # contains a double hyphen
    RESERVED        = 'reserved'          # on the reserved-slug list
    PROFANE         = 'profane'           # caught by the basic profanity filter
