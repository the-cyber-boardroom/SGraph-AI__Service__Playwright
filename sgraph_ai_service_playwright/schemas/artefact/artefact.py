# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Vault, S3, Local File, and Artefact Reference Schemas
# (spec §5.3)
#
# Schema__Artefact__Ref is a discriminated union expressed via nullable fields:
# exactly one of {vault_ref, s3_ref, local_ref, inline_b64} is populated per
# artefact, determined by `sink`.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous          import Safe_Str__Text__Dangerous
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                   import Safe_Str__Version
from osbot_utils.type_safe.primitives.domains.cryptography.safe_str.Safe_Str__Hash                import Safe_Str__Hash
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path                 import Safe_Str__File__Path
from osbot_utils.type_safe.primitives.domains.files.safe_uint.Safe_UInt__FileSize                 import Safe_UInt__FileSize
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                  import Timestamp_Now
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id                   import Safe_Str__Id

from sgraph_ai_service_playwright.schemas.enums.enums                                             import (
    Enum__Artefact__Sink                                                                          ,
    Enum__Artefact__Type                                                                          ,
)
from sgraph_ai_service_playwright.schemas.primitives.s3                                           import (
    Safe_Str__S3_Bucket                                                                           ,
    Safe_Str__S3_Key                                                                              ,
)
from sgraph_ai_service_playwright.schemas.primitives.vault                                        import (
    Safe_Str__Vault_Key                                                                           ,
    Safe_Str__Vault_Path                                                                          ,
)


class Schema__Vault_Ref(Type_Safe):                                                 # Points to a file in a vault
    vault_key           : Safe_Str__Vault_Key                                       # "drum-hunt-6610" or opaque
    path                : Safe_Str__Vault_Path                                      # e.g. /config/proxy.json
    version             : Safe_Str__Version = None                                  # Optional snapshot pin


class Schema__S3_Ref(Type_Safe):                                                    # Points to an S3 object
    bucket              : Safe_Str__S3_Bucket
    key                 : Safe_Str__S3_Key
    version             : Safe_Str__Id = None                                       # S3 object version ID if bucket versioned


class Schema__Local_File_Ref(Type_Safe):                                            # Points to a local filesystem path
    path                : Safe_Str__File__Path                                      # Rejected on Lambda / Claude Web


class Schema__Artefact__Sink_Config(Type_Safe):                                     # Where one artefact type goes (per-type capture config)
    enabled             : bool = False                                              # Is this artefact type captured?
    sink                : Enum__Artefact__Sink = Enum__Artefact__Sink.INLINE
    sink_vault_ref      : Schema__Vault_Ref = None                                  # Required if sink=VAULT (the output vault)
    sink_s3_bucket      : Safe_Str__S3_Bucket = None                                # Required if sink=S3
    sink_s3_prefix      : Safe_Str__S3_Key   = None                                 # Key prefix; artefact name appended
    sink_local_folder   : Safe_Str__File__Path = None                               # Required if sink=LOCAL_FILE


class Schema__Artefact__Ref(Type_Safe):                                             # Reference to an artefact after capture
    artefact_type       : Enum__Artefact__Type
    sink                : Enum__Artefact__Sink
    size_bytes          : Safe_UInt__FileSize                                       # Always populated
    content_hash        : Safe_Str__Hash = None                                     # Optional content hash
    vault_ref           : Schema__Vault_Ref      = None                             # Populated when sink=VAULT
    s3_ref              : Schema__S3_Ref         = None                             # Populated when sink=S3
    local_ref           : Schema__Local_File_Ref = None                             # Populated when sink=LOCAL_FILE
    inline_b64          : Safe_Str__Text__Dangerous = None                          # Populated when sink=INLINE (base64)
    captured_at         : Timestamp_Now
