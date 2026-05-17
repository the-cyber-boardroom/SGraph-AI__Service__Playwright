# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — Observe__Agent__Tracer
# Queries all registered sources for events tagged with a given session_id.
# Correlation tag key: sg:session-id.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query import Source__Query
from sgraph_ai_service_playwright__cli.aws.observe.Source__Registry              import Source__Registry


class Observe__Agent__Tracer(Type_Safe):
    registry : Source__Registry

    def trace(self, session_id: str, since: str = '24h') -> list:      # list[dict] — all matched events
        results   = []
        query_txt = session_id                                          # each source searches for the session_id
        for entry in self.registry.list_sources():
            name    = entry['name']
            adapter = entry['adapter']
            streams = adapter.list_streams()
            for stream_ref in streams:
                stream_name = stream_ref if isinstance(stream_ref, str) else stream_ref.name
                q = Source__Query(
                    text   = query_txt,
                    source = name,
                    stream = stream_name,
                    since  = since,
                    limit  = 100,
                )
                try:
                    page = adapter.query(q)
                    for ev in page.events:
                        results.append({
                            'source'    : name,
                            'stream'    : stream_name,
                            'timestamp' : ev.timestamp,
                            'message'   : ev.message,
                        })
                except Exception:
                    pass
        return results

    def trace_summary(self, session_id: str, since: str = '24h') -> dict:
        events    = self.trace(session_id, since=since)
        by_source = {}
        for ev in events:
            src = ev['source']
            by_source[src] = by_source.get(src, 0) + 1
        return {
            'session_id'   : session_id,
            'total_events' : len(events),
            'by_source'    : by_source,
            'events'       : events,
        }
