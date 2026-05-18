# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Source__Adapter
# Registration is LAZY (not at import); registry empty at foundation; register_all
# returns 1 source.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Source__Adapter import Lab__Source__Adapter
from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry          import Source__Registry


class test_Lab__Source__Adapter(TestCase):

    def test_1__import_does_not_auto_register(self):
        # Just importing Lab__Source__Adapter must not call register_all
        from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Source__Adapter import Lab__Source__Adapter
        registry = Source__Registry()
        assert registry.source_names() == []                                       # registry is empty after import

    def test_2__list_streams_empty_at_foundation(self):
        adapter = Lab__Source__Adapter()
        assert adapter.list_streams() == []

    def test_3__connect_returns_true(self):
        adapter = Lab__Source__Adapter()
        assert adapter.connect() is True

    def test_4__register_all_returns_1(self):
        registry = Source__Registry()
        count    = Lab__Source__Adapter.register_all(registry)
        assert count == 1

    def test_5__register_all_adds_lab_source(self):
        registry = Source__Registry()
        Lab__Source__Adapter.register_all(registry)
        assert 'lab' in registry.source_names()

    def test_6__registered_adapter_is_Lab__Source__Adapter(self):
        registry = Source__Registry()
        Lab__Source__Adapter.register_all(registry)
        adapter  = registry.get_source('lab')
        assert isinstance(adapter, Lab__Source__Adapter)

    def test_7__calling_register_all_twice_overwrites_not_duplicates(self):
        registry = Source__Registry()
        Lab__Source__Adapter.register_all(registry)
        Lab__Source__Adapter.register_all(registry)
        assert registry.source_names().count('lab') == 1
