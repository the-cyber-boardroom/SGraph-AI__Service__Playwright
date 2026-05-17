# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Vault__Fetcher__In_Memory
# In-memory stand-in for the send.sgraph.ai fetch. Test and local composition
# seed a vault folder with publish(); fetch() looks it up by (Transfer-ID, read
# key). Folders are immutable here exactly as they are in SG/API — publish() of
# an already-present ref is a no-op-overwrite-free assertion path for tests.
# ═══════════════════════════════════════════════════════════════════════════════

from vault_publish.schemas.Schema__Manifest__Signature       import Schema__Manifest__Signature
from vault_publish.schemas.Schema__Vault__Folder_Ref         import Schema__Vault__Folder_Ref
from vault_publish.schemas.Schema__Vault_App__Manifest       import Schema__Vault_App__Manifest
from vault_publish.service.Vault__Fetcher                    import Vault__Fetcher


class Vault__Fetcher__In_Memory(Vault__Fetcher):
    _folders : dict                                                          # (transfer_id, read_key) → (manifest, signature)

    def publish(self, folder_ref : Schema__Vault__Folder_Ref         ,
                      manifest    : Schema__Vault_App__Manifest       ,
                      signature   : Schema__Manifest__Signature       ) -> None:
        self._folders[self._key(folder_ref)] = (manifest, signature)

    def fetch(self, folder_ref: Schema__Vault__Folder_Ref) -> tuple:
        entry = self._folders.get(self._key(folder_ref))
        if entry is None:
            return None, None
        return entry

    def _key(self, folder_ref: Schema__Vault__Folder_Ref) -> tuple:
        return (str(folder_ref.transfer_id), str(folder_ref.read_key))
