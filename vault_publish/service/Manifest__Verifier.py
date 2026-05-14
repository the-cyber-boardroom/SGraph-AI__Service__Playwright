# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Manifest__Verifier
# Verifies a provisioning manifest's detached signature against the signing
# public key referenced by the slug's billing record. This runs in the wake
# sequence BEFORE any instance is started — a failed verify stops the wake. It
# is the line between "an attacker can run provisioning on our infra" and "an
# attacker writes bytes we ignore".
#
# PROPOSED — the signing scheme and key custody are open question #4 in the dev
# pack and are owned by SG/Send. Manifest__Verifier__In_Memory is the stand-in
# used for tests and local composition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Schema__Manifest__Signature       import Schema__Manifest__Signature
from vault_publish.schemas.Schema__Slug__Billing_Record      import Schema__Slug__Billing_Record
from vault_publish.schemas.Schema__Vault_App__Manifest       import Schema__Vault_App__Manifest


class Manifest__Verifier(Type_Safe):

    def verify(self, manifest        : Schema__Vault_App__Manifest    ,
                     signature       : Schema__Manifest__Signature    ,
                     billing_record  : Schema__Slug__Billing_Record   ) -> bool:
        raise NotImplementedError(
            'Manifest__Verifier.verify is blocked on SG/Send open question #4 '
            '(the manifest signing scheme). Use Manifest__Verifier__In_Memory '
            'for tests and local composition.')
