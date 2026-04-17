# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Artefact__Writer (v2 spec §4.8; v1 source not in pack)
#
# THE ONLY class that writes to artefact sinks (spec §10 bullet: "the only class
# that writes to sinks"). Responsibilities:
#
#   • write_artefact(artefact_type, data, sink_config) -> Schema__Artefact__Ref
#         — Dispatch bytes to the configured sink and return a typed Ref.
#         — INLINE:     base64-encodes into ref.inline_b64  (pure, no deps).
#         — VAULT:      delegates to write_bytes_to_vault (seam).
#         — S3:         delegates to write_bytes_to_s3    (seam).
#         — LOCAL_FILE: writes to disk via write_bytes_to_local (seam).
#
#   • read_from_vault(vault_ref)            -> dict                (JSON helper)
#   • write_to_vault(vault_ref, data: dict) -> None                (JSON helper)
#         — Used by Credentials__Loader for cookies / storage state.
#
# Sink-write seams (read_from_vault / write_to_vault / write_bytes_to_vault /
# write_bytes_to_s3 / write_bytes_to_local) are plain methods that subclasses
# override to plug in the real vault HTTP client / osbot-aws S3 adapter / etc.
# The unit test uses an in-memory subclass. The real wiring lands when the
# vault and S3 clients get introduced — integration-test territory.
#
# Method surface derived from v2 spec callsites (routes-catalogue-v2.md
# lines 988, 993, 1002, 1159). The v2 §4.8 note "unchanged from v1" is not
# actionable without v1 source, so this is the smallest surface that
# satisfies all known callers.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import hashlib
import os
from typing                                                                                      import Any

from osbot_utils.type_safe.Type_Safe                                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous          import Safe_Str__Text__Dangerous
from osbot_utils.type_safe.primitives.domains.cryptography.safe_str.Safe_Str__Hash               import Safe_Str__Hash
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path                import Safe_Str__File__Path
from osbot_utils.type_safe.primitives.domains.files.safe_uint.Safe_UInt__FileSize                import Safe_UInt__FileSize

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                         import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Sink_Config                 import Schema__Artefact__Sink_Config
from sgraph_ai_service_playwright.schemas.artefact.Schema__Local_File_Ref                        import Schema__Local_File_Ref
from sgraph_ai_service_playwright.schemas.artefact.Schema__S3_Ref                                import Schema__S3_Ref
from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                             import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                             import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type                             import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.primitives.s3.Safe_Str__S3_Key                         import Safe_Str__S3_Key


HASH_LEN = 10                                                                       # Safe_Str__Hash is exactly 10 hex chars (40 bits) — identity, not crypto


class Artefact__Writer(Type_Safe):

    vault_client : Any = None                                                       # Real vault HTTP client — subclass/DI provides; None = seam-only
    s3_client    : Any = None                                                       # osbot-aws S3 adapter                    — same pattern

    def write_artefact(self                                                       ,
                       artefact_type : Enum__Artefact__Type                       ,
                       data          : bytes                                      ,
                       sink_config   : Schema__Artefact__Sink_Config
                  ) -> Schema__Artefact__Ref:

        if not sink_config.enabled:                                                 # Capture switched off for this artefact type
            return None

        size_bytes   = Safe_UInt__FileSize(len(data))
        content_hash = Safe_Str__Hash(hashlib.sha256(data).hexdigest()[:HASH_LEN])
        ref          = Schema__Artefact__Ref(artefact_type = artefact_type ,
                                             sink          = sink_config.sink ,
                                             size_bytes    = size_bytes    ,
                                             content_hash  = content_hash  )

        sink = sink_config.sink
        if   sink == Enum__Artefact__Sink.INLINE     : ref.inline_b64 = self.encode_inline(data)
        elif sink == Enum__Artefact__Sink.VAULT      : ref.vault_ref  = self.write_bytes_to_vault(sink_config.sink_vault_ref, artefact_type, data)
        elif sink == Enum__Artefact__Sink.S3         : ref.s3_ref     = self.write_bytes_to_s3   (sink_config.sink_s3_bucket, sink_config.sink_s3_prefix, artefact_type, data)
        elif sink == Enum__Artefact__Sink.LOCAL_FILE : ref.local_ref  = self.write_bytes_to_local(sink_config.sink_local_folder, artefact_type, data)

        return ref

    def encode_inline(self, data: bytes) -> Safe_Str__Text__Dangerous:
        return Safe_Str__Text__Dangerous(base64.b64encode(data).decode('ascii'))

    # ─── Sink seams — subclasses / DI replace these with real adapters ─────────

    def write_bytes_to_vault(self                                       ,
                             vault_ref     : Schema__Vault_Ref           ,
                             artefact_type : Enum__Artefact__Type        ,
                             data          : bytes
                        ) -> Schema__Vault_Ref:
        raise NotImplementedError('Artefact__Writer.write_bytes_to_vault requires a vault client (override in subclass or wire DI)')

    def write_bytes_to_s3(self                                  ,
                          bucket        : Any                   ,                   # Safe_Str__S3_Bucket
                          prefix        : Safe_Str__S3_Key      ,
                          artefact_type : Enum__Artefact__Type  ,
                          data          : bytes
                     ) -> Schema__S3_Ref:
        raise NotImplementedError('Artefact__Writer.write_bytes_to_s3 requires an S3 client (override in subclass or wire DI)')

    def write_bytes_to_local(self                                        ,
                             folder        : Safe_Str__File__Path         ,
                             artefact_type : Enum__Artefact__Type         ,
                             data          : bytes
                        ) -> Schema__Local_File_Ref:
        os.makedirs(str(folder), exist_ok=True)
        filename = self.build_local_filename(artefact_type, data)
        path     = Safe_Str__File__Path(os.path.join(str(folder), filename))
        with open(str(path), 'wb') as f:
            f.write(data)
        return Schema__Local_File_Ref(path=path)

    def build_local_filename(self, artefact_type: Enum__Artefact__Type, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()[:HASH_LEN]
        ext    = FILENAME_EXTENSIONS.get(artefact_type, 'bin')
        return f'{artefact_type.value}_{digest}.{ext}'

    # ─── Vault JSON helpers — Credentials__Loader contract ─────────────────────

    def read_from_vault(self, vault_ref: Schema__Vault_Ref) -> dict:
        raise NotImplementedError('Artefact__Writer.read_from_vault requires a vault client (override in subclass or wire DI)')

    def write_to_vault(self, vault_ref: Schema__Vault_Ref, data: dict) -> None:
        raise NotImplementedError('Artefact__Writer.write_to_vault requires a vault client (override in subclass or wire DI)')

    # ─── capture_* — typed convenience wrappers used by Step__Executor ──────────
    #
    # Step__Executor is the only class permitted to call page.*; it captures the
    # bytes and hands them here. capture_*() pins the artefact_type so callers
    # don't have to repeat it. Returns None when the sink_config is disabled
    # (same semantics as write_artefact).

    def capture_screenshot(self                                          ,
                           data        : bytes                           ,
                           sink_config : Schema__Artefact__Sink_Config
                      ) -> Schema__Artefact__Ref:
        return self.write_artefact(Enum__Artefact__Type.SCREENSHOT, data, sink_config)

    def capture_page_content(self                                          ,
                             data        : bytes                           ,
                             sink_config : Schema__Artefact__Sink_Config
                        ) -> Schema__Artefact__Ref:
        return self.write_artefact(Enum__Artefact__Type.PAGE_CONTENT, data, sink_config)

    def capture_pdf(self                                          ,
                    data        : bytes                           ,
                    sink_config : Schema__Artefact__Sink_Config
               ) -> Schema__Artefact__Ref:
        return self.write_artefact(Enum__Artefact__Type.PDF, data, sink_config)


FILENAME_EXTENSIONS = { Enum__Artefact__Type.SCREENSHOT   : 'png'  ,
                        Enum__Artefact__Type.VIDEO        : 'webm' ,
                        Enum__Artefact__Type.PDF          : 'pdf'  ,
                        Enum__Artefact__Type.HAR          : 'har'  ,
                        Enum__Artefact__Type.TRACE        : 'zip'  ,
                        Enum__Artefact__Type.CONSOLE_LOG  : 'log'  ,
                        Enum__Artefact__Type.NETWORK_LOG  : 'log'  ,
                        Enum__Artefact__Type.PAGE_CONTENT : 'html' }
