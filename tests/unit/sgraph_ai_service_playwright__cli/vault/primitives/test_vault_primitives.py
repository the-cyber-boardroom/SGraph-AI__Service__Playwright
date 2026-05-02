# ═══════════════════════════════════════════════════════════════════════════════
# Tests — vault primitives
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Int__Bytes        import Safe_Int__Bytes
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime import Safe_Str__ISO_Datetime
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Plugin__Type_Id import Safe_Str__Plugin__Type_Id
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__SHA256       import Safe_Str__SHA256
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Stack__Id    import Safe_Str__Stack__Id
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle import Safe_Str__Vault__Handle
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Path  import Safe_Str__Vault__Path


class test_vault_primitives(TestCase):

    def test_plugin_type_id__accepts_known_ids(self):
        for pid in ('docker', 'firefox', 'podman', 'elastic', 'vnc'):
            assert str(Safe_Str__Plugin__Type_Id(pid)) == pid

    def test_plugin_type_id__replaces_uppercase(self):
        assert str(Safe_Str__Plugin__Type_Id('Firefox')) == '_irefox'           # F replaced by _

    def test_stack_id__accepts_global(self):
        assert str(Safe_Str__Stack__Id('_global')) == '_global'

    def test_stack_id__accepts_stack_name(self):
        assert str(Safe_Str__Stack__Id('quiet-fermi')) == 'quiet-fermi'

    def test_vault_handle__accepts_slug(self):
        for h in ('credentials', 'mitm-script', 'profile', 'profile.tar.gz'):
            assert str(Safe_Str__Vault__Handle(h)) == h

    def test_vault_handle__strips_spaces(self):
        assert str(Safe_Str__Vault__Handle('my handle')) == 'my_handle'         # space stripped

    def test_sha256__accepts_hex_digest(self):
        digest = 'a' * 64
        assert str(Safe_Str__SHA256(digest)) == digest

    def test_sha256__replaces_uppercase(self):
        assert str(Safe_Str__SHA256('ABCDEF')) == '______'                       # all replaced; [a-f0-9] only

    def test_iso_datetime__accepts_valid(self):
        ts = '2026-05-02T14:32:00Z'
        assert str(Safe_Str__ISO_Datetime(ts)) == ts

    def test_vault_path__accepts_slash_path(self):
        p = 'plugin/firefox/_global/mitm-script'
        assert str(Safe_Str__Vault__Path(p)) == p

    def test_safe_int_bytes__zero_default(self):
        assert int(Safe_Int__Bytes()) == 0

    def test_safe_int_bytes__accepts_positive(self):
        assert int(Safe_Int__Bytes(1024)) == 1024

    def test_safe_int_bytes__rejects_negative(self):
        import pytest
        with pytest.raises(ValueError):
            Safe_Int__Bytes(-1)
