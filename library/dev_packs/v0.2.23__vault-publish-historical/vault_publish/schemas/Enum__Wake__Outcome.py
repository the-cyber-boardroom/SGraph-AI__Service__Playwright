# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Wake__Outcome
# The result of running the wake sequence for a slug.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Wake__Outcome(str, Enum):
    ALREADY_RUNNING          = 'already-running'           # instance was already healthy
    STARTED                  = 'started'                   # instance was stopped, now starting
    REJECTED_INVALID_SLUG    = 'rejected-invalid-slug'     # slug failed validation — nothing started
    REJECTED_NOT_REGISTERED  = 'rejected-not-registered'   # no billing record for the slug
    REJECTED_VAULT_NOT_FOUND = 'rejected-vault-not-found'  # no vault folder at the derived location
    REJECTED_UNVERIFIED      = 'rejected-unverified'       # manifest signature failed — nothing started
    REJECTED_BAD_MANIFEST    = 'rejected-bad-manifest'     # manifest could not be interpreted
