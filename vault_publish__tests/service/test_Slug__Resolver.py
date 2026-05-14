# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Slug__Resolver + Slug__Resolver__In_Memory (no mocks, no patches)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Safe_Str__Slug              import Safe_Str__Slug
from vault_publish.schemas.Schema__Vault__Folder_Ref   import Schema__Vault__Folder_Ref
from vault_publish.service.Slug__Resolver              import Slug__Resolver
from vault_publish.service.Slug__Resolver__In_Memory   import Slug__Resolver__In_Memory


class test_Slug__Resolver(TestCase):

    def test_base_resolver_raises_not_implemented(self):                     # SG/Send boundary — open question #1
        with self.assertRaises(NotImplementedError):
            Slug__Resolver().resolve(Safe_Str__Slug('sara-cv'))

    def test_in_memory_returns_folder_ref(self):
        ref = Slug__Resolver__In_Memory().resolve(Safe_Str__Slug('sara-cv'))
        assert isinstance(ref, Schema__Vault__Folder_Ref)
        assert str(ref.transfer_id) != ''
        assert str(ref.read_key)    != ''

    def test_in_memory_is_deterministic(self):                               # same slug → same pair
        resolver = Slug__Resolver__In_Memory()
        a = resolver.resolve(Safe_Str__Slug('sara-cv'))
        b = resolver.resolve(Safe_Str__Slug('sara-cv'))
        assert str(a.transfer_id) == str(b.transfer_id)
        assert str(a.read_key)    == str(b.read_key)

    def test_in_memory_distinct_slugs_distinct_refs(self):
        resolver = Slug__Resolver__In_Memory()
        a = resolver.resolve(Safe_Str__Slug('sara-cv'))
        b = resolver.resolve(Safe_Str__Slug('demo-site'))
        assert str(a.transfer_id) != str(b.transfer_id)
