# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Source__Contract behaviour contract
# Exercises a stub adapter to lock the Source__Contract signatures hard.
# Every source adapter (Slice A, F, H) must satisfy this contract.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract     import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query        import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page  import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream       import Source__Stream


class _Stub__Source__Adapter(Source__Contract):
    _connected : bool = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def list_streams(self) -> list:
        return ['stream-a', 'stream-b']

    def tail(self, stream: str, since: str) -> Source__Stream:
        return Source__Stream(source='stub', stream=stream)

    def query(self, q: Source__Query) -> Source__Result__Page:
        return Source__Result__Page()

    def stats(self, stream: str, agg: str) -> dict:
        return {'count': 0}

    def schema(self, stream: str) -> dict:
        return {'fields': []}


class Test__Source__Contract__Behaviour:

    def setup_method(self):
        self.adapter = _Stub__Source__Adapter()

    def test_connect_returns_bool(self):
        result = self.adapter.connect()
        assert isinstance(result, bool)
        assert result is True

    def test_list_streams_returns_list(self):
        result = self.adapter.list_streams()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_tail_returns_source_stream(self):
        result = self.adapter.tail('my-stream', '1h')
        assert isinstance(result, Source__Stream)

    def test_query_returns_result_page(self):
        q = Source__Query(text='errors', limit=10)
        result = self.adapter.query(q)
        assert isinstance(result, Source__Result__Page)

    def test_stats_returns_dict(self):
        result = self.adapter.stats('my-stream', 'count')
        assert isinstance(result, dict)

    def test_schema_returns_dict(self):
        result = self.adapter.schema('my-stream')
        assert isinstance(result, dict)

    def test_stream_is_iterable(self):
        stream = self.adapter.tail('s', '1h')
        events = list(stream)
        assert events == []
