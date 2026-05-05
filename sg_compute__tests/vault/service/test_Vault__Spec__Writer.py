# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault__Spec__Writer (no mocks, no patches)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.vault.enums.Enum__Vault__Error_Code                          import Enum__Vault__Error_Code
from sg_compute.vault.schemas.Schema__Vault__Write__Receipt                  import Schema__Vault__Write__Receipt
from sg_compute.vault.service.Vault__Spec__Writer                            import SHARED_STACK_ID, Vault__Spec__Writer


def _registry(*spec_ids: str) -> Spec__Registry:
    r = Spec__Registry()
    for sid in spec_ids:
        r.register(Schema__Spec__Manifest__Entry(spec_id=sid))
    return r


def _writer(spec_ids=('firefox',), handles_by_spec=None, vault_attached=True) -> Vault__Spec__Writer:
    handles = handles_by_spec if handles_by_spec is not None else {'firefox': {'credentials', 'mitm-script', 'profile'}}
    return Vault__Spec__Writer(
        spec_registry         = _registry(*spec_ids),
        write_handles_by_spec = handles,
        vault_attached        = vault_attached,
    )


class test_Vault__Spec__Writer(TestCase):

    # ── write ────────────────────────────────────────────────────────────────

    def test_write__no_vault_returns_error(self):
        w            = _writer(vault_attached=False)
        receipt, err = w.write('firefox', '_shared', 'credentials', b'x')
        assert receipt is None
        assert err     == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_write__unknown_spec_returns_error(self):
        w            = _writer()
        receipt, err = w.write('no-such-spec', '_shared', 'credentials', b'x')
        assert receipt is None
        assert err     == Enum__Vault__Error_Code.UNKNOWN_SPEC

    def test_write__disallowed_handle_returns_error(self):
        w            = _writer()
        receipt, err = w.write('firefox', '_shared', 'not-declared', b'x')
        assert receipt is None
        assert err     == Enum__Vault__Error_Code.DISALLOWED_HANDLE

    def test_write__payload_too_large_returns_error(self):
        w            = _writer()
        big          = b'x' * (10 * 1024 * 1024 + 1)
        receipt, err = w.write('firefox', '_shared', 'credentials', big)
        assert receipt is None
        assert err     == Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE

    def test_write__success_returns_receipt(self):
        w            = _writer()
        receipt, err = w.write('firefox', '_shared', 'credentials', b'secret')
        assert err     is None
        assert isinstance(receipt, Schema__Vault__Write__Receipt)

    def test_write__receipt_fields(self):
        w            = _writer()
        body         = b'hello vault'
        receipt, _   = w.write('firefox', 'stack-123', 'mitm-script', body)
        assert str(receipt.spec_id)       == 'firefox'
        assert str(receipt.stack_id)      == 'stack-123'
        assert str(receipt.handle)        == 'mitm-script'
        assert int(receipt.bytes_written) == len(body)
        assert len(str(receipt.sha256))   == 64
        assert str(receipt.vault_path)    == 'spec/firefox/stack-123/mitm-script'

    def test_write__sha256_is_correct(self):
        import hashlib
        w            = _writer()
        body         = b'deterministic content'
        receipt, _   = w.write('firefox', '_shared', 'credentials', body)
        assert str(receipt.sha256) == hashlib.sha256(body).hexdigest()

    def test_write__shared_stack_id_allowed(self):
        w            = _writer()
        receipt, err = w.write('firefox', SHARED_STACK_ID, 'profile', b'data')
        assert err   is None
        assert str(receipt.stack_id) == SHARED_STACK_ID

    def test_write__vault_path_uses_spec_prefix(self):
        w            = _writer()
        receipt, _   = w.write('firefox', '_shared', 'credentials', b'x')
        assert str(receipt.vault_path).startswith('spec/')

    def test_write__no_handle_restriction_when_handles_empty(self):
        w            = _writer(handles_by_spec={'firefox': set()})
        receipt, err = w.write('firefox', '_shared', 'any-handle', b'x')
        assert err   is None                                               # empty set = unrestricted

    def test_write__no_registry_skips_spec_validation(self):
        w = Vault__Spec__Writer(vault_attached=True)                      # no spec_registry
        receipt, err = w.write('any-spec', '_shared', 'any-handle', b'x')
        assert err   is None

    # ── list_spec ────────────────────────────────────────────────────────────

    def test_list_spec__no_vault_returns_error(self):
        w              = _writer(vault_attached=False)
        receipts, err  = w.list_spec('firefox')
        assert receipts is None
        assert err      == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_list_spec__unknown_spec_returns_error(self):
        w              = _writer()
        receipts, err  = w.list_spec('unknown')
        assert receipts is None
        assert err      == Enum__Vault__Error_Code.UNKNOWN_SPEC

    def test_list_spec__known_spec_returns_empty_list(self):
        w              = _writer()
        receipts, err  = w.list_spec('firefox')
        assert err     is None
        assert list(receipts) == []

    # ── delete ───────────────────────────────────────────────────────────────

    def test_delete__no_vault_returns_error(self):
        w       = _writer(vault_attached=False)
        ok, err = w.delete('firefox', '_shared', 'credentials')
        assert ok  is False
        assert err == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_delete__unknown_spec_returns_error(self):
        w       = _writer()
        ok, err = w.delete('no-spec', '_shared', 'credentials')
        assert ok  is False
        assert err == Enum__Vault__Error_Code.UNKNOWN_SPEC

    def test_delete__disallowed_handle_returns_error(self):
        w       = _writer()
        ok, err = w.delete('firefox', '_shared', 'bad-handle')
        assert ok  is False
        assert err == Enum__Vault__Error_Code.DISALLOWED_HANDLE

    def test_delete__success(self):
        w       = _writer()
        ok, err = w.delete('firefox', '_shared', 'credentials')
        assert err is None
        assert ok  is True

    # ── SHARED_STACK_ID constant ─────────────────────────────────────────────

    def test_shared_stack_id_value(self):
        assert SHARED_STACK_ID == '_shared'
