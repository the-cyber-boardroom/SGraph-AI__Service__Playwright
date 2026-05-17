# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Publish__Error_Code
# Orchestrator-level errors returned by Publish__Service. Slug-validation and
# manifest-interpretation errors have their own enums; these are the errors that
# only the orchestrator can determine.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Publish__Error_Code(str, Enum):
    SLUG_TAKEN      = 'slug-taken'         # a billing record already exists for the slug
    NOT_REGISTERED  = 'not-registered'     # no billing record for the slug
    VAULT_NOT_FOUND = 'vault-not-found'    # no vault folder at the slug's derived location
