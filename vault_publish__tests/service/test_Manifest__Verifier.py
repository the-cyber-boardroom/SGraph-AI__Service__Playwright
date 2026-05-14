# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Manifest__Verifier + Manifest__Verifier__In_Memory (no mocks)
# Verification must succeed for an untampered, correctly-keyed manifest and fail
# for a tampered manifest or a wrong key — that is the line between code-on-our-
# infra and bytes-we-ignore.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Vault_App__Runtime      import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type         import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Manifest__Path      import Safe_Str__Manifest__Path
from vault_publish.schemas.Safe_Str__Owner_Id            import Safe_Str__Owner_Id
from vault_publish.schemas.Safe_Str__Signing_Key_Ref     import Safe_Str__Signing_Key_Ref
from vault_publish.schemas.Safe_Str__Slug                import Safe_Str__Slug
from vault_publish.schemas.Schema__Manifest__Signature   import Schema__Manifest__Signature
from vault_publish.schemas.Schema__Slug__Billing_Record  import Schema__Slug__Billing_Record
from vault_publish.schemas.Schema__Vault_App__Manifest   import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Verifier            import Manifest__Verifier
from vault_publish.service.Manifest__Verifier__In_Memory import Manifest__Verifier__In_Memory


def _manifest() -> Schema__Vault_App__Manifest:
    return Schema__Vault_App__Manifest(app_type     = Enum__Vault_App__Type.STATIC_SITE ,
                                       runtime      = Enum__Vault_App__Runtime.STATIC   ,
                                       content_root = Safe_Str__Manifest__Path('public'),
                                       health_path  = Safe_Str__Manifest__Path('healthz'))


def _billing(key_ref='key-ref-1') -> Schema__Slug__Billing_Record:
    return Schema__Slug__Billing_Record(slug                   = Safe_Str__Slug('sara-cv')              ,
                                        owner_id               = Safe_Str__Owner_Id('owner-1')          ,
                                        signing_public_key_ref = Safe_Str__Signing_Key_Ref(key_ref)     )


class test_Manifest__Verifier(TestCase):

    def test_base_verifier_raises_not_implemented(self):                     # SG/Send boundary — open question #4
        verifier = Manifest__Verifier()
        with self.assertRaises(NotImplementedError):
            verifier.verify(_manifest(), Schema__Manifest__Signature(), _billing())

    def test_in_memory_verifies_correctly_signed_manifest(self):
        verifier  = Manifest__Verifier__In_Memory()
        manifest  = _manifest()
        signature = verifier.sign(manifest, 'key-ref-1')
        assert verifier.verify(manifest, signature, _billing('key-ref-1')) is True

    def test_in_memory_rejects_tampered_manifest(self):
        verifier  = Manifest__Verifier__In_Memory()
        manifest  = _manifest()
        signature = verifier.sign(manifest, 'key-ref-1')
        manifest.health_path = Safe_Str__Manifest__Path('changed')           # tamper after signing
        assert verifier.verify(manifest, signature, _billing('key-ref-1')) is False

    def test_in_memory_rejects_wrong_key(self):
        verifier  = Manifest__Verifier__In_Memory()
        manifest  = _manifest()
        signature = verifier.sign(manifest, 'key-ref-1')
        assert verifier.verify(manifest, signature, _billing('different-key')) is False
