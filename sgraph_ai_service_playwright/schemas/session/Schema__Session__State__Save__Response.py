# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__State__Save__Response (spec §5.5)
#
# Response for POST /session/save-state/{id} — confirms the storage-state JSON
# was persisted to the given vault_ref and stamps the write time.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                                import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id


class Schema__Session__State__Save__Response(Type_Safe):                            # POST /session/save-state/{id} response
    session_id              : Session_Id
    vault_ref               : Schema__Vault_Ref                                     # Where the state was written
    saved_at                : Timestamp_Now
