# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — CloudTrail__Source__Adapter
# Source__Contract adapter backed by CloudTrail__AWS__Client.
# Trails are treated as streams; tail/query use lookup_events.
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
from sgraph_ai_service_playwright__cli.aws.cloudtrail.service.CloudTrail__AWS__Client             import CloudTrail__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Time__Parser                        import Logs__Time__Parser


class CloudTrail__Source__Adapter(Source__Contract):
    ct_client   : CloudTrail__AWS__Client
    time_parser : Logs__Time__Parser
    _connected  : bool = False

    def connect(self) -> bool:
        try:
            self.ct_client.list_trails()
            self._connected = True
            return True
        except Exception:
            return False

    def list_streams(self) -> list:                                     # trails are streams
        try:
            trails = self.ct_client.list_trails()
        except Exception:
            return []
        refs = []
        for t in trails:
            name = t if isinstance(t, str) else t.get('Name', t.get('TrailARN', ''))
            refs.append(Schema__Source__Stream__Ref(name=name, description='CloudTrail trail'))
        return refs

    def tail(self, stream: str, since: str) -> Source__Stream:          # stream = trail name (or '' for all)
        def _gen():
            try:
                raw_events = self.ct_client.lookup_events(max_results=50)
            except Exception:
                return
            for ev in raw_events:
                event_time = str(ev.get('EventTime', '')) if isinstance(ev, dict) else ''
                event_name = ev.get('EventName', '') if isinstance(ev, dict) else str(ev)
                yield Schema__AWS__Source__Event(
                    timestamp = event_time,
                    source    = 'cloudtrail',
                    stream    = stream,
                    message   = event_name,
                    raw       = ev if isinstance(ev, dict) else {'event': str(ev)},
                )
        return Source__Stream(source='cloudtrail', stream=stream).with_generator(_gen())

    def query(self, q: Source__Query) -> Source__Result__Page:
        try:
            raw_events = self.ct_client.lookup_events(
                attribute_key   = 'EventName' if q.text else '',
                attribute_value = q.text,
                max_results     = q.limit,
            )
        except Exception:
            return Source__Result__Page()
        events = []
        for ev in raw_events:
            event_time = str(ev.get('EventTime', '')) if isinstance(ev, dict) else ''
            event_name = ev.get('EventName', '') if isinstance(ev, dict) else str(ev)
            events.append(Schema__AWS__Source__Event(
                timestamp = event_time,
                source    = 'cloudtrail',
                stream    = q.stream,
                message   = event_name,
                raw       = ev if isinstance(ev, dict) else {'event': str(ev)},
            ))
        return Source__Result__Page(events=events, total_count=len(events))

    def stats(self, stream: str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats:
        try:
            raw_events = self.ct_client.lookup_events(max_results=1000)
        except Exception:
            raw_events = []
        agg_val = agg.value if hasattr(agg, 'value') else str(agg)
        return Schema__Source__Stats(
            stream      = stream,
            aggregation = agg_val,
            total       = len(raw_events),
            buckets     = [],
        )

    def schema(self, stream: str) -> Schema__Source__Stream__Schema:
        fields = [
            Schema__Source__Field(name='EventTime',   type_hint='datetime', nullable=True),
            Schema__Source__Field(name='EventName',   type_hint='str',      nullable=False),
            Schema__Source__Field(name='EventId',     type_hint='str',      nullable=True),
            Schema__Source__Field(name='Username',    type_hint='str',      nullable=True),
            Schema__Source__Field(name='Resources',   type_hint='list',     nullable=True),
        ]
        return Schema__Source__Stream__Schema(stream=stream, fields=fields)
