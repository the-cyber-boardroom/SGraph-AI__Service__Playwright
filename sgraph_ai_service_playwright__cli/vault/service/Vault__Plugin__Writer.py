# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault__Plugin__Writer
# Validates a vault-write request and produces a receipt. Actual vault
# persistence goes through the existing vault layer (out-of-scope for this
# contract slice — stubbed below and replaced when vault I/O lands).
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from datetime                                                                           import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                    import Plugin__Registry
from sgraph_ai_service_playwright__cli.vault.enums.Enum__Vault__Error_Code              import Enum__Vault__Error_Code
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Int__Bytes                 import Safe_Int__Bytes
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime          import Safe_Str__ISO_Datetime
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Plugin__Type_Id       import Safe_Str__Plugin__Type_Id
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__SHA256                import Safe_Str__SHA256
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Stack__Id             import Safe_Str__Stack__Id
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle         import Safe_Str__Vault__Handle
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Path           import Safe_Str__Vault__Path
from sgraph_ai_service_playwright__cli.vault.schemas.Schema__Vault__Write__Receipt      import Schema__Vault__Write__Receipt
from sgraph_ai_service_playwright__cli.vault.collections.List__Schema__Vault__Write__Receipt import List__Schema__Vault__Write__Receipt

MAX_BLOB_BYTES    = 10 * 1024 * 1024                                                   # 10 MB default cap
GLOBAL_STACK_ID   = '_global'


class Vault__Plugin__Writer(Type_Safe):
    plugin_registry : Plugin__Registry
    vault_attached  : bool = False                                                     # True when a vault token is wired up

    # ── validation helpers ───────────────────────────────────────────────────

    def _validate_plugin_id(self, plugin_id: str) -> str | None:                       # None = valid; str = error code
        if plugin_id not in self.plugin_registry.manifests:
            return Enum__Vault__Error_Code.UNKNOWN_PLUGIN
        return None

    def _validate_handle(self, plugin_id: str, handle: str) -> str | None:
        manifest      = self.plugin_registry.manifests.get(plugin_id)
        if manifest is None:
            return Enum__Vault__Error_Code.UNKNOWN_PLUGIN
        allowed       = {str(h) for h in manifest.write_handles}
        if allowed and handle not in allowed:                                           # empty list = no restriction
            return Enum__Vault__Error_Code.DISALLOWED_HANDLE
        return None

    def _validate_size(self, body: bytes) -> str | None:
        if len(body) > MAX_BLOB_BYTES:
            return Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE
        return None

    # ── public API ────────────────────────────────────────────────────────────

    def write(self, plugin_id: str, stack_id: str, handle: str,
              body: bytes) -> tuple[Schema__Vault__Write__Receipt | None, str | None]:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_plugin_id(plugin_id)
        if err:
            return None, err
        err = self._validate_handle(plugin_id, handle)
        if err:
            return None, err
        err = self._validate_size(body)
        if err:
            return None, err
        vault_path = f'plugin/{plugin_id}/{stack_id}/{handle}'
        sha256     = hashlib.sha256(body).hexdigest()
        written_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        receipt = Schema__Vault__Write__Receipt(
            plugin_id     = Safe_Str__Plugin__Type_Id(plugin_id)  ,
            stack_id      = Safe_Str__Stack__Id(stack_id)         ,
            handle        = Safe_Str__Vault__Handle(handle)       ,
            bytes_written = Safe_Int__Bytes(len(body))            ,
            sha256        = Safe_Str__SHA256(sha256)              ,
            written_at    = Safe_Str__ISO_Datetime(written_at)    ,
            vault_path    = Safe_Str__Vault__Path(vault_path)     ,
        )
        return receipt, None

    def get_metadata(self, plugin_id: str, stack_id: str,
                     handle: str) -> tuple[Schema__Vault__Write__Receipt | None, str | None]:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_plugin_id(plugin_id)
        if err:
            return None, err
        return None, None                                                               # stub: real lookup in follow-on

    def list_plugin(self, plugin_id: str) -> tuple[List__Schema__Vault__Write__Receipt | None, str | None]:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_plugin_id(plugin_id)
        if err:
            return None, err
        return List__Schema__Vault__Write__Receipt(), None                             # stub: real vault scan in follow-on

    def delete(self, plugin_id: str, stack_id: str,
               handle: str) -> tuple[bool, str | None]:
        if not self.vault_attached:
            return False, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_plugin_id(plugin_id)
        if err:
            return False, err
        err = self._validate_handle(plugin_id, handle)
        if err:
            return False, err
        return True, None                                                               # stub: real vault delete in follow-on
