# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Source__Registry
# 6 tests exercising registration, lookup, and listing.
# Uses _Stub__Source__Adapter — no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry import Source__Registry
from tests.unit.sgraph_ai_service_playwright__cli.aws.observe._Stub__Source__Adapter import _Stub__Source__Adapter


class Test__Source__Registry:

    def setup_method(self):
        self.registry = Source__Registry()
        self.adapter  = _Stub__Source__Adapter()
        self.adapter.add_stream('stream-a')
        self.adapter.add_stream('stream-b')

    def test_1__register_and_list(self):
        self.registry.register('stub', self.adapter)
        sources = self.registry.list_sources()
        assert len(sources) == 1
        assert sources[0]['name'] == 'stub'

    def test_2__get_source_returns_adapter(self):
        self.registry.register('stub', self.adapter)
        got = self.registry.get_source('stub')
        assert got is self.adapter

    def test_3__get_source_missing_returns_none(self):
        result = self.registry.get_source('nonexistent')
        assert result is None

    def test_4__source_names_returns_list(self):
        self.registry.register('s3',         _Stub__Source__Adapter())
        self.registry.register('cloudwatch', _Stub__Source__Adapter())
        names = self.registry.source_names()
        assert 's3'         in names
        assert 'cloudwatch' in names

    def test_5__multiple_adapters(self):
        adapter2 = _Stub__Source__Adapter()
        self.registry.register('stub',  self.adapter)
        self.registry.register('stub2', adapter2)
        sources = self.registry.list_sources()
        assert len(sources) == 2

    def test_6__list_sources_empty_registry(self):
        sources = self.registry.list_sources()
        assert sources == []
