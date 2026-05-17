# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Control_Plane__Client
# Drives provisioning through the per-instance control-plane FastAPI.
#
# generate_key() mints a random, single-use, per-instance key — delivered to the
# instance via EC2 user-data / IMDSv2, never over a CloudFront-facing channel.
# provision() pushes the allowlisted plan; a key is accepted exactly once (the
# _used_keys ledger enforces single-use). The real implementation POSTs the plan
# to the instance control-plane authenticated with the key, then the control-
# plane setup endpoint closes — that HTTP call is the marked seam; the key
# lifecycle and recorded plan run here in-memory.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Safe_Str__Control_Plane__Key      import Safe_Str__Control_Plane__Key
from vault_publish.schemas.Safe_Str__Instance__Id            import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.schemas.Schema__Provisioning__Plan        import Schema__Provisioning__Plan


class Control_Plane__Client(Type_Safe):
    _provisioned : dict                                                      # slug(str) → Schema__Provisioning__Plan
    _used_keys   : dict                                                      # key(str)  → slug(str)  (single-use ledger)

    def generate_key(self) -> Safe_Str__Control_Plane__Key:
        return Safe_Str__Control_Plane__Key(secrets.token_urlsafe(32))

    def provision(self, slug              : Safe_Str__Slug               ,
                        instance_id       : Safe_Str__Instance__Id       ,
                        control_plane_key : Safe_Str__Control_Plane__Key ,
                        plan              : Schema__Provisioning__Plan   ) -> bool:
        key = str(control_plane_key)
        if key in self._used_keys:                                           # single-use: never accept a key twice
            return False
        # ── seam: real impl POSTs `plan` to the control-plane FastAPI on
        #    `instance_id`, authenticated with `control_plane_key`; on success
        #    the control-plane setup endpoint closes.
        self._used_keys[key]         = str(slug)
        self._provisioned[str(slug)] = plan
        return True

    def provisioned_plan(self, slug: Safe_Str__Slug):
        return self._provisioned.get(str(slug))
