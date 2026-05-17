# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Manifest__Verifier__In_Memory
# Deterministic stand-in for the real signing scheme. A signature is valid when:
#   - its signing_key_ref matches the billing record's signing_public_key_ref, and
#   - its value equals sha256(sorted-manifest-json + signing_key_ref).
# Test and local composition produce a valid signature with sign(); tampering
# with the manifest or using the wrong key makes verify() return False. This is
# NOT a real signing scheme — it carries the property (payload + key → verifiable
# signature), not the cryptography.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import json

from vault_publish.schemas.Safe_Str__Message                 import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Signature__Value        import Safe_Str__Signature__Value
from vault_publish.schemas.Safe_Str__Signing_Key_Ref         import Safe_Str__Signing_Key_Ref
from vault_publish.schemas.Schema__Manifest__Signature       import Schema__Manifest__Signature
from vault_publish.schemas.Schema__Slug__Billing_Record      import Schema__Slug__Billing_Record
from vault_publish.schemas.Schema__Vault_App__Manifest       import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Verifier                import Manifest__Verifier


class Manifest__Verifier__In_Memory(Manifest__Verifier):

    def expected_value(self, manifest         : Schema__Vault_App__Manifest ,
                             signing_key_ref  : str                         ) -> str:
        body = json.dumps(manifest.json(), sort_keys=True)
        return hashlib.sha256((body + str(signing_key_ref)).encode()).hexdigest()

    def sign(self, manifest         : Schema__Vault_App__Manifest ,
                   signing_key_ref  : str                         ) -> Schema__Manifest__Signature:
        return Schema__Manifest__Signature(
            algorithm       = Safe_Str__Message        ('in-memory-sha256')                       ,
            value           = Safe_Str__Signature__Value(self.expected_value(manifest, signing_key_ref)),
            signing_key_ref = Safe_Str__Signing_Key_Ref (str(signing_key_ref))                    ,
        )

    def verify(self, manifest        : Schema__Vault_App__Manifest    ,
                     signature       : Schema__Manifest__Signature    ,
                     billing_record  : Schema__Slug__Billing_Record   ) -> bool:
        if str(signature.signing_key_ref) != str(billing_record.signing_public_key_ref):
            return False
        expected = self.expected_value(manifest, billing_record.signing_public_key_ref)
        return str(signature.value) == expected
