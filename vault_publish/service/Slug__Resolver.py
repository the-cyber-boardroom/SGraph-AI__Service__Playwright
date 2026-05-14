# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Slug__Resolver
# Derives a slug to its SG/API (Transfer-ID, read key) pair.
#
# PROPOSED — the derivation reuses SG/Send's existing "simple token" mechanism.
# The exact algorithm is open question #1 in the dev pack and is owned by
# SG/Send; the real derivation cannot be written until that contract is
# confirmed. Slug__Resolver__In_Memory is the deterministic stand-in used for
# tests and local composition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.schemas.Schema__Vault__Folder_Ref         import Schema__Vault__Folder_Ref


class Slug__Resolver(Type_Safe):

    def resolve(self, slug: Safe_Str__Slug) -> Schema__Vault__Folder_Ref:
        raise NotImplementedError(
            'Slug__Resolver.resolve is blocked on SG/Send open question #1 '
            '(the simple-token derivation contract). Use Slug__Resolver__In_Memory '
            'for tests and local composition.')
