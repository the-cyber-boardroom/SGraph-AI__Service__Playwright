# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _Stub__Source__Adapter
# In-memory fake implementing Source__Contract.
# No mocks. No patches. Used by all observe unit tests.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Enum__Source__Aggregation      import Enum__Source__Aggregation
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stats          import Schema__Source__Stats
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Ref    import Schema__Source__Stream__Ref
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Schema import Schema__Source__Stream__Schema, Schema__Source__Field
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract               import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query                  import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page           import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream                 import Source__Stream
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event             import Schema__AWS__Source__Event


class _Stub__Source__Adapter(Source__Contract):
    _connected : bool = False
    _streams   : list
    _events    : list                                                   # list[Schema__AWS__Source__Event]

    def add_stream(self, name: str) -> None:
        self._streams.append(Schema__Source__Stream__Ref(name=name, description='stub stream'))

    def add_event(self, timestamp: str, message: str, stream: str = 'stub-stream') -> None:
        self._events.append(Schema__AWS__Source__Event(
            timestamp = timestamp,
            source    = 'stub',
            stream    = stream,
            message   = message,
            raw       = {},
        ))

    def connect(self) -> bool:
        self._connected = True
        return True

    def list_streams(self) -> list:
        return list(self._streams)

    def tail(self, stream: str, since: str) -> Source__Stream:
        events = [ev for ev in self._events if ev.stream == stream or not stream]

        def _gen():
            yield from events

        return Source__Stream(source='stub', stream=stream).with_generator(_gen())

    def query(self, q: Source__Query) -> Source__Result__Page:
        matched = [ev for ev in self._events if q.text.lower() in ev.message.lower()]
        matched = matched[:q.limit]
        return Source__Result__Page(events=matched, total_count=len(matched))

    def stats(self, stream: str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats:
        agg_val = agg.value if hasattr(agg, 'value') else str(agg)
        events  = [ev for ev in self._events if ev.stream == stream or not stream]
        return Schema__Source__Stats(
            stream      = stream,
            aggregation = agg_val,
            total       = len(events),
            buckets     = [],
        )

    def schema(self, stream: str) -> Schema__Source__Stream__Schema:
        return Schema__Source__Stream__Schema(
            stream = stream,
            fields = [Schema__Source__Field(name='message', type_hint='str', nullable=False)],
        )
