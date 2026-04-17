# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Artefact__Sink_Config (spec §5.3)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path                import Safe_Str__File__Path

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                             import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                             import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.primitives.s3.Safe_Str__S3_Bucket                      import Safe_Str__S3_Bucket
from sgraph_ai_service_playwright.schemas.primitives.s3.Safe_Str__S3_Key                         import Safe_Str__S3_Key


class Schema__Artefact__Sink_Config(Type_Safe):                                     # Where one artefact type goes (per-type capture config)
    enabled           : bool = False                                                # Is this artefact type captured?
    sink              : Enum__Artefact__Sink = Enum__Artefact__Sink.INLINE
    sink_vault_ref    : Schema__Vault_Ref      = None                               # Required if sink=VAULT (the output vault)
    sink_s3_bucket    : Safe_Str__S3_Bucket    = None                               # Required if sink=S3
    sink_s3_prefix    : Safe_Str__S3_Key       = None                               # Key prefix; artefact name appended
    sink_local_folder : Safe_Str__File__Path   = None                               # Required if sink=LOCAL_FILE
