# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Slug__Resolver__In_Memory
# Deterministic stand-in for the SG/Send simple-token derivation: hashes the
# slug to a stable (Transfer-ID, read key) pair. Same slug → same pair, which is
# the property the real derivation must also have. This is NOT the real
# algorithm — it exists so the orchestrator can be composed and tested without
# the SG/Send contract.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib

from vault_publish.schemas.Safe_Str__Read_Key                import Safe_Str__Read_Key
from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.schemas.Safe_Str__Transfer_Id             import Safe_Str__Transfer_Id
from vault_publish.schemas.Schema__Vault__Folder_Ref         import Schema__Vault__Folder_Ref
from vault_publish.service.Slug__Resolver                    import Slug__Resolver


class Slug__Resolver__In_Memory(Slug__Resolver):

    def resolve(self, slug: Safe_Str__Slug) -> Schema__Vault__Folder_Ref:
        digest = hashlib.sha256(str(slug).encode()).hexdigest()
        return Schema__Vault__Folder_Ref(
            transfer_id = Safe_Str__Transfer_Id(digest[:32])  ,
            read_key    = Safe_Str__Read_Key   (digest[32:64]),
        )
