# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Artefact__Ref (spec §5.3)
#
# Discriminated union expressed via nullable fields: exactly one of
# {vault_ref, s3_ref, local_ref, inline_b64} is populated per artefact,
# determined by `sink`.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                               import Type_Safe
from osbot_utils.type_safe.primitives.domains.cryptography.safe_str.Safe_Str__Hash                 import Safe_Str__Hash
from osbot_utils.type_safe.primitives.domains.files.safe_uint.Safe_UInt__FileSize                  import Safe_UInt__FileSize
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                   import Timestamp_Now

from sgraph_ai_service_playwright.schemas.artefact.Schema__Local_File_Ref                          import Schema__Local_File_Ref
from sgraph_ai_service_playwright.schemas.artefact.Schema__S3_Ref                                  import Schema__S3_Ref
from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                               import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                               import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type                               import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.primitives.text.Safe_Str__Artefact__Inline               import Safe_Str__Artefact__Inline


class Schema__Artefact__Ref(Type_Safe):                                             # Reference to an artefact after capture
    artefact_type : Enum__Artefact__Type
    sink          : Enum__Artefact__Sink
    size_bytes    : Safe_UInt__FileSize                                             # Always populated
    content_hash  : Safe_Str__Hash                = None                            # Optional content hash
    vault_ref     : Schema__Vault_Ref             = None                            # Populated when sink=VAULT
    s3_ref        : Schema__S3_Ref                = None                            # Populated when sink=S3
    local_ref     : Schema__Local_File_Ref        = None                            # Populated when sink=LOCAL_FILE
    inline_b64    : Safe_Str__Artefact__Inline    = None                            # Populated when sink=INLINE (base64) — 20 MB limit covers real screenshots/PDFs; the 64 KB default of Safe_Str__Text__Dangerous is too small
    captured_at   : Timestamp_Now
