# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Vault__Fetcher
# Fetches the immutable vault folder from send.sgraph.ai by (Transfer-ID, read
# key) and extracts the provisioning manifest and its detached signature.
#
# PROPOSED — the fetch endpoint contract is open question #3 in the dev pack and
# is owned by SG/Send. The real fetch cannot be written until that contract is
# confirmed. Vault__Fetcher__In_Memory is the stand-in used for tests and local
# composition.
#
# fetch() returns (manifest, signature). Both are None when no vault folder
# exists at the derived location.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Schema__Vault__Folder_Ref         import Schema__Vault__Folder_Ref


class Vault__Fetcher(Type_Safe):

    def fetch(self, folder_ref: Schema__Vault__Folder_Ref) -> tuple:        # -> (manifest|None, signature|None)
        raise NotImplementedError(
            'Vault__Fetcher.fetch is blocked on SG/Send open question #3 '
            '(the send.sgraph.ai fetch contract). Use Vault__Fetcher__In_Memory '
            'for tests and local composition.')
