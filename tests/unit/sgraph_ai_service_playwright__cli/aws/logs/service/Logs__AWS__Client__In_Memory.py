# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__AWS__Client__In_Memory
# In-memory fake boto3 CloudWatch Logs client for unit tests.
# No mocks. No patches. Dict-backed dispatch.
#
# Group store:  _groups[name] = {'logGroupName': ..., 'retentionInDays': ...,
#                                 'logGroupArn': ..., 'storedBytes': ...}
# Event store:  _events[group_name] = list of event dicts
# Insights queries supported at result level — tests provide canned rows.
# ═══════════════════════════════════════════════════════════════════════════════

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client import Logs__AWS__Client


class _Fake_Logs_Client:                                                         # minimal boto3-alike CloudWatch Logs client backed by dict stores

    def __init__(self, groups_store: dict, events_store: dict, query_results: dict):
        self._groups_store  = groups_store    # name -> raw group dict
        self._events_store  = events_store    # group_name -> list of event dicts
        self._query_results = query_results   # query_id -> result dict
        self._next_query_id = 1

    # ── paginator ─────────────────────────────────────────────────────────────

    def get_paginator(self, method: str):
        return _Fake_Logs_Paginator(self, method)

    # ── describe_log_groups ───────────────────────────────────────────────────

    def describe_log_groups(self, logGroupNamePrefix: str = '', **_) -> dict:
        groups = list(self._groups_store.values())
        if logGroupNamePrefix:
            groups = [g for g in groups if g['logGroupName'].startswith(logGroupNamePrefix)]
        return {'logGroups': groups}

    # ── create_log_group ──────────────────────────────────────────────────────

    def create_log_group(self, logGroupName: str, **_):
        if logGroupName in self._groups_store:
            raise ClientError(
                {'Error': {'Code'   : 'ResourceAlreadyExistsException',
                           'Message': f'Log group already exists: {logGroupName}'}},
                'CreateLogGroup',
            )
        self._groups_store[logGroupName] = {
            'logGroupName'   : logGroupName,
            'logGroupArn'    : f'arn:aws:logs:eu-west-2:123456789012:log-group:{logGroupName}',
            'storedBytes'    : 0,
        }

    # ── put_retention_policy ──────────────────────────────────────────────────

    def put_retention_policy(self, logGroupName: str, retentionInDays: int, **_):
        if logGroupName in self._groups_store:
            self._groups_store[logGroupName]['retentionInDays'] = retentionInDays

    # ── delete_log_group ──────────────────────────────────────────────────────

    def delete_log_group(self, logGroupName: str, **_):
        if logGroupName not in self._groups_store:
            raise ClientError(
                {'Error': {'Code'   : 'ResourceNotFoundException',
                           'Message': f'Log group not found: {logGroupName}'}},
                'DeleteLogGroup',
            )
        del self._groups_store[logGroupName]

    # ── filter_log_events ─────────────────────────────────────────────────────

    def filter_log_events(self, logGroupName: str, startTime: int,
                          endTime: int = None, filterPattern: str = '',
                          logStreamNamePrefix: str = '',
                          logStreamNames: list = None, limit: int = 100, **_):
        events = list(self._events_store.get(logGroupName, []))
        events = [e for e in events if e.get('timestamp', 0) >= startTime]
        if endTime:
            events = [e for e in events if e.get('timestamp', 0) <= endTime]
        if filterPattern:
            events = [e for e in events if filterPattern.lower() in e.get('message', '').lower()]
        if logStreamNamePrefix:
            events = [e for e in events
                      if e.get('logStreamName', '').startswith(logStreamNamePrefix)]
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


class _Fake_Logs_Paginator:

    def __init__(self, fake_client: _Fake_Logs_Client, method: str):
        self._client = fake_client
        self._method = method

    def paginate(self, **kwargs):
        if self._method == 'describe_log_groups':
            yield self._client.describe_log_groups(
                logGroupNamePrefix=kwargs.get('logGroupNamePrefix', ''))


class Logs__AWS__Client__In_Memory(Logs__AWS__Client):

    def __init__(self, events_store: dict = None, query_results: dict = None):
        super().__init__()
        self._groups        = {}
        self._store         = events_store  if events_store  is not None else {}
        self._query_results = query_results if query_results is not None else {}
        self._fake          = _Fake_Logs_Client(self._groups, self._store, self._query_results)

    def client(self):
        return self._fake

    # ── seeding helpers ──────────────────────────────────────────────────────

    def seed_group(self, name: str, retention_days: int = 7,
                   stored_bytes: int = 0) -> str:          # returns name
        self._groups[name] = {
            'logGroupName'   : name,
            'logGroupArn'    : f'arn:aws:logs:eu-west-2:123456789012:log-group:{name}',
            'storedBytes'    : stored_bytes,
        }
        if retention_days:
            self._groups[name]['retentionInDays'] = retention_days
        return name

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

    def seed_event(self, group: str, stream: str, message: str,
                   timestamp_ms: int = None):               # convenience alias
        import time
        ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
        self.add_event(log_group=group, timestamp=ts, message=message, stream=stream)

    def add_query_result(self, query_id: str, rows: list, status: str = 'Complete'):
        result_rows = []
        for row_dict in rows:
            result_rows.append([{'field': k, 'value': v} for k, v in row_dict.items()])
        self._query_results[query_id] = {'status': status, 'results': result_rows}
