# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault__Plugin__Writer
# No mocks: fake registry wired with Plugin__Manifest__Firefox.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry            import Plugin__Registry
from sgraph_ai_service_playwright__cli.firefox.plugin.Plugin__Manifest__Firefox import Plugin__Manifest__Firefox
from sgraph_ai_service_playwright__cli.vault.enums.Enum__Vault__Error_Code      import Enum__Vault__Error_Code
from sgraph_ai_service_playwright__cli.vault.schemas.Schema__Vault__Write__Receipt import Schema__Vault__Write__Receipt
from sgraph_ai_service_playwright__cli.vault.service.Vault__Plugin__Writer      import Vault__Plugin__Writer


def _registry() -> Plugin__Registry:
    r = Plugin__Registry()
    r.manifests['firefox'] = Plugin__Manifest__Firefox()
    return r


def _writer(vault_attached: bool = True) -> Vault__Plugin__Writer:
    return Vault__Plugin__Writer(plugin_registry=_registry(), vault_attached=vault_attached)


class test_Vault__Plugin__Writer(TestCase):

    def test_write__no_vault_returns_409_code(self):
        w                = _writer(vault_attached=False)
        receipt, err     = w.write('firefox', '_global', 'credentials', b'secret')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_write__unknown_plugin_returns_error(self):
        w                = _writer()
        receipt, err     = w.write('unknown-plugin', '_global', 'credentials', b'data')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.UNKNOWN_PLUGIN

    def test_write__disallowed_handle_returns_error(self):
        w                = _writer()
        receipt, err     = w.write('firefox', '_global', 'not-declared-handle', b'data')
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.DISALLOWED_HANDLE

    def test_write__payload_too_large(self):
        w                = _writer()
        big_body         = b'x' * (10 * 1024 * 1024 + 1)
        receipt, err     = w.write('firefox', '_global', 'credentials', big_body)
        assert receipt   is None
        assert err       == Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE

    def test_write__success_returns_receipt(self):
        w                = _writer()
        receipt, err     = w.write('firefox', '_global', 'credentials', b'my-secret-bytes')
        assert err       is None
        assert isinstance(receipt, Schema__Vault__Write__Receipt)

    def test_write__receipt_fields(self):
        w                = _writer()
        body             = b'hello vault'
        receipt, _       = w.write('firefox', 'stack-123', 'mitm-script', body)
        assert str(receipt.plugin_id)    == 'firefox'
        assert str(receipt.stack_id)     == 'stack-123'
        assert str(receipt.handle)       == 'mitm-script'
        assert int(receipt.bytes_written) == len(body)
        assert len(str(receipt.sha256))  == 64
        assert str(receipt.vault_path)   == 'plugin/firefox/stack-123/mitm-script'

    def test_write__sha256_is_correct(self):
        import hashlib
        w                = _writer()
        body             = b'deterministic content'
        receipt, _       = w.write('firefox', '_global', 'credentials', body)
        expected         = hashlib.sha256(body).hexdigest()
        assert str(receipt.sha256) == expected

    def test_write__global_stack_id_allowed(self):
        w                = _writer()
        receipt, err     = w.write('firefox', '_global', 'profile', b'profile-data')
        assert err       is None
        assert str(receipt.stack_id) == '_global'

    def test_list__no_vault_returns_error(self):
        w                = _writer(vault_attached=False)
        receipts, err    = w.list_plugin('firefox')
        assert receipts  is None
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_list__unknown_plugin_returns_error(self):
        w                = _writer()
        receipts, err    = w.list_plugin('unknown')
        assert receipts  is None
        assert err       == Enum__Vault__Error_Code.UNKNOWN_PLUGIN

    def test_list__returns_empty_list_for_known_plugin(self):
        w                = _writer()
        receipts, err    = w.list_plugin('firefox')
        assert err       is None
        assert list(receipts) == []

    def test_delete__no_vault_returns_error(self):
        w                = _writer(vault_attached=False)
        ok, err          = w.delete('firefox', '_global', 'credentials')
        assert ok        is False
        assert err       == Enum__Vault__Error_Code.NO_VAULT_ATTACHED

    def test_delete__success(self):
        w                = _writer()
        ok, err          = w.delete('firefox', '_global', 'credentials')
        assert err       is None
        assert ok        is True

    def test_firefox_write_handles_declared(self):
        m                = Plugin__Manifest__Firefox()
        handles          = {str(h) for h in m.write_handles}
        assert handles   == {'credentials', 'mitm-script', 'profile'}
