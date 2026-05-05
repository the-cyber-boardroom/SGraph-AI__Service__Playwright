# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault__Spec__Writer (via legacy shim path)
# Retargeted to sg_compute.vault in BV2.9. Shim alias kept for one release.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.vault.enums.Enum__Vault__Error_Code                          import Enum__Vault__Error_Code
from sg_compute.vault.schemas.Schema__Vault__Write__Receipt                  import Schema__Vault__Write__Receipt
from sg_compute.vault.service.Vault__Spec__Writer                            import SHARED_STACK_ID, Vault__Spec__Writer

FIREFOX_HANDLES = {'credentials', 'mitm-script', 'profile'}


def _writer(vault_attached=True) -> Vault__Spec__Writer:
    return Vault__Spec__Writer(
        write_handles_by_spec = {'firefox': FIREFOX_HANDLES},
        vault_attached        = vault_attached,
    )


class test_Vault__Plugin__Writer(TestCase):

    def test_write__no_vault_returns_409_code(self):
        w                = _writer(vault_attached=False)
        receipt, err     = w.write('firefox', SHARED_STACK_ID, 'credentials', b'secret')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_write__unknown_plugin_returns_error(self):
        w                = _writer()
        receipt, err     = w.write('unknown-plugin', SHARED_STACK_ID, 'credentials', b'data')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.UNKNOWN_SPEC              # renamed from UNKNOWN_PLUGIN

    def test_write__disallowed_handle_returns_error(self):
        w                = _writer()
        receipt, err     = w.write('firefox', SHARED_STACK_ID, 'not-declared-handle', b'data')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.DISALLOWED_HANDLE

    def test_write__payload_too_large(self):
        w                = _writer()
        big_body         = b'x' * (10 * 1024 * 1024 + 1)
        receipt, err     = w.write('firefox', SHARED_STACK_ID, 'credentials', big_body)
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE

    def test_write__success_returns_receipt(self):
        w                = _writer()
        receipt, err     = w.write('firefox', SHARED_STACK_ID, 'credentials', b'my-secret-bytes')
        assert err       is None
        assert isinstance(receipt, Schema__Vault__Write__Receipt)

    def test_write__receipt_fields(self):
        w                = _writer()
        body             = b'hello vault'
        receipt, _       = w.write('firefox', 'stack-123', 'mitm-script', body)
        assert str(receipt.spec_id)       == 'firefox'
        assert str(receipt.stack_id)      == 'stack-123'
        assert str(receipt.handle)        == 'mitm-script'
        assert int(receipt.bytes_written) == len(body)
        assert len(str(receipt.sha256))   == 64
        assert str(receipt.vault_path)    == 'spec/firefox/stack-123/mitm-script'

    def test_write__sha256_is_correct(self):
        import hashlib
        w                = _writer()
        body             = b'deterministic content'
        receipt, _       = w.write('firefox', SHARED_STACK_ID, 'credentials', body)
        expected         = hashlib.sha256(body).hexdigest()
        assert str(receipt.sha256) == expected

    def test_write__global_stack_id_allowed(self):
        w                = _writer()
        receipt, err     = w.write('firefox', SHARED_STACK_ID, 'profile', b'profile-data')
        assert err       is None
        assert str(receipt.stack_id) == SHARED_STACK_ID

    def test_list__no_vault_returns_error(self):
        w                = _writer(vault_attached=False)
        receipts, err    = w.list_spec('firefox')
        assert receipts  is None
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_list__unknown_plugin_returns_error(self):
        w                = _writer()
        receipts, err    = w.list_spec('unknown')
        assert receipts  is None
        assert err       == Enum__Vault__Error_Code.UNKNOWN_SPEC

    def test_list__returns_empty_list_for_known_plugin(self):
        w                = _writer()
        receipts, err    = w.list_spec('firefox')
        assert err       is None
        assert list(receipts) == []

    def test_delete__no_vault_returns_error(self):
        w                = _writer(vault_attached=False)
        ok, err          = w.delete('firefox', SHARED_STACK_ID, 'credentials')
        assert ok        is False
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_delete__success(self):
        w                = _writer()
        w.write('firefox', SHARED_STACK_ID, 'credentials', b'test-data')
        ok, err          = w.delete('firefox', SHARED_STACK_ID, 'credentials')
        assert err       is None
        assert ok        is True

    def test_firefox_write_handles_declared(self):
        assert FIREFOX_HANDLES == {'credentials', 'mitm-script', 'profile'}
