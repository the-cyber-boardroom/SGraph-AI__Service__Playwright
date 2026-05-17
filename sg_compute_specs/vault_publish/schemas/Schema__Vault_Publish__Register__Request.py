# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__Register__Request
# Flat scheme — no namespace field (decided 2026-05-17, Q3).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug       import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key import Safe_Str__Vault__Key


class Schema__Vault_Publish__Register__Request(Type_Safe):
    slug      : Safe_Str__Slug       = None
    vault_key : Safe_Str__Vault__Key = None
    region    : str                  = ''
