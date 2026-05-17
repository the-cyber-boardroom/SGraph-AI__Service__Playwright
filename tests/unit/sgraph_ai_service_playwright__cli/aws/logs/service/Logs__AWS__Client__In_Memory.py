# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__AWS__Client__In_Memory
# In-memory fake boto3 CloudWatch Logs client for unit tests.
# No mocks. No patches. Dict-backed dispatch.
#
# Event store keyed by (log_group, log_stream, event_id).
# Insights queries supported at result level — tests provide canned rows.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client import Logs__AWS__Client


class _Fake_Logs_Client:
    """Minimal boto3-alike CloudWatch Logs client backed by dict stores."""

    def __init__(self, events_store: dict, query_results: dict):
        self._events_store  = events_store    # log_group -> list of event dicts
        self._query_results = query_results   # query_id  -> result dict
        self._next_query_id = 1

    # ── filter_log_events ─────────────────────────────────────────────────────

    def filter_log_events(self, logGroupName: str, startTime: int,
                          endTime: int = None, filterPattern: str = '',
                          logStreamNames: list = None, limit: int = 100, **_):
        events = list(self._events_store.get(logGroupName, []))
        events = [e for e in events if e.get('timestamp', 0) >= startTime]
        if endTime:
            events = [e for e in events if e.get('timestamp', 0) <= endTime]
        if filterPattern:
            events = [e for e in events if filterPattern.lower() in e.get('message', '').lower()]
        if logStreamNames:
            events = [e for e in events if e.get('logStreamName', '') in logStreamNames]
        events = events[:limit]
        return {'events': events, 'searchedLogStreams': []}

    # ── start_query ───────────────────────────────────────────────────────────

    def start_query(self, logGroupName: str, startTime: int, endTime: int,
                    queryString: str, **_) -> dict:
        qid = str(self._next_query_id)
        self._next_query_id += 1
        return {'queryId': qid}

    # ── get_query_results ─────────────────────────────────────────────────────

    def get_query_results(self, queryId: str) -> dict:
        if queryId in self._query_results:
            return self._query_results[queryId]
        return {'status': 'Complete', 'results': []}


class Logs__AWS__Client__In_Memory(Logs__AWS__Client):

    def __init__(self, events_store: dict = None, query_results: dict = None):
        super().__init__()
        self._store         = events_store  if events_store  is not None else {}
        self._query_results = query_results if query_results is not None else {}
        self._fake          = _Fake_Logs_Client(self._store, self._query_results)

    def client(self):
        return self._fake

    def add_event(self, log_group: str, timestamp: int, message: str,
                  stream: str = 'stream/001', event_id: str = None):
        if log_group not in self._store:
            self._store[log_group] = []
        evt_id = event_id or f'evt-{len(self._store[log_group])}'
        self._store[log_group].append({
            'eventId'      : evt_id,
            'timestamp'    : timestamp,
            'logStreamName': stream,
            'message'      : message,
        })

    def add_query_result(self, query_id: str, rows: list, status: str = 'Complete'):
        result_rows = []
        for row_dict in rows:
            result_rows.append([{'field': k, 'value': v} for k, v in row_dict.items()])
        self._query_results[query_id] = {'status': status, 'results': result_rows}
