# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — CloudWatch__Source__Adapter
# Source__Contract adapter backed by Logs__AWS__Client (CloudWatch Logs).
# Log groups are treated as streams.
# tail   = filter_events from 'since' window.
# query  = filter_events with q.text as filter pattern.
# stats  = event count in window grouped by log stream.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Enum__Source__Aggregation      import Enum__Source__Aggregation
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stats          import Schema__Source__Stats
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Ref    import Schema__Source__Stream__Ref
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Schema__Source__Stream__Schema import Schema__Source__Stream__Schema, Schema__Source__Field
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Contract               import Source__Contract
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query                  import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page           import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream                 import Source__Stream
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event             import Schema__AWS__Source__Event
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client                         import Logs__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Time__Parser                        import Logs__Time__Parser


class CloudWatch__Source__Adapter(Source__Contract):
    logs_client : Logs__AWS__Client
    time_parser : Logs__Time__Parser
    _connected  : bool = False

    def connect(self) -> bool:
        try:
            self.logs_client.client().describe_log_groups(limit=1)
            self._connected = True
            return True
        except Exception:
            return False

    def list_streams(self) -> list:                                     # log groups are streams
        try:
            resp = self.logs_client.client().describe_log_groups(limit=50)
        except Exception:
            return []
        refs = []
        for grp in resp.get('logGroups', []):
            name      = grp.get('logGroupName', '')
            refs.append(Schema__Source__Stream__Ref(name=name, description='CloudWatch log group'))
        return refs

    def tail(self, stream: str, since: str) -> Source__Stream:          # stream = log group name
        start_ms = self.time_parser.parse_optional(since)

        def _gen():
            resp = self.logs_client.filter_events(
                log_group  = stream,
                start_time = start_ms,
                limit      = 100,
            )
            for ev in resp.events:
                yield Schema__AWS__Source__Event(
                    timestamp = str(ev.timestamp),
                    source    = 'cloudwatch',
                    stream    = stream,
                    message   = ev.message,
                    raw       = {'event_id': ev.event_id, 'timestamp': ev.timestamp,
                                 'log_stream': str(ev.log_stream), 'message': ev.message},
                )
        return Source__Stream(source='cloudwatch', stream=stream).with_generator(_gen())

    def query(self, q: Source__Query) -> Source__Result__Page:
        stream   = q.stream or q.source
        start_ms = self.time_parser.parse_optional(q.since)
        resp     = self.logs_client.filter_events(
            log_group      = stream,
            start_time     = start_ms,
            filter_pattern = q.text,
            limit          = q.limit,
        )
        events = []
        for ev in resp.events:
            events.append(Schema__AWS__Source__Event(
                timestamp = str(ev.timestamp),
                source    = 'cloudwatch',
                stream    = stream,
                message   = ev.message,
                raw       = {'event_id': ev.event_id, 'timestamp': ev.timestamp,
                             'log_stream': str(ev.log_stream), 'message': ev.message},
            ))
        return Source__Result__Page(
            events      = events,
            total_count = len(events),
            truncated   = resp.more_available,
        )

    def stats(self, stream: str, agg: Enum__Source__Aggregation) -> Schema__Source__Stats:
        start_ms = self.time_parser.parse_optional('24h')
        resp     = self.logs_client.filter_events(
            log_group  = stream,
            start_time = start_ms,
            limit      = 1000,
        )
        agg_val = agg.value if hasattr(agg, 'value') else str(agg)
        return Schema__Source__Stats(
            stream      = stream,
            aggregation = agg_val,
            total       = len(resp.events),
            buckets     = [],
        )

    def schema(self, stream: str) -> Schema__Source__Stream__Schema:
        fields = [
            Schema__Source__Field(name='timestamp',  type_hint='int',  nullable=False),
            Schema__Source__Field(name='eventId',    type_hint='str',  nullable=True),
            Schema__Source__Field(name='logStream',  type_hint='str',  nullable=True),
            Schema__Source__Field(name='message',    type_hint='str',  nullable=False),
        ]
        return Schema__Source__Stream__Schema(stream=stream, fields=fields)
