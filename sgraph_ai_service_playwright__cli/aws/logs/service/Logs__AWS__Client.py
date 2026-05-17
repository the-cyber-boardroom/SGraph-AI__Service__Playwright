# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__AWS__Client
# CloudWatch Logs access: filter events, Insights queries.
#
# EXCEPTION — boto3 used directly. osbot_aws does not cover FilterLogEvents,
# StartQuery, or GetQueryResults at the level needed here.  This module is
# the sole boto3 boundary for CloudWatch Logs — subclasses override client()
# to inject fakes for tests.
# ═══════════════════════════════════════════════════════════════════════════════

import time

import boto3                                                                      # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.logs.primitives.Safe_Str__Log__Stream import Safe_Str__Log__Stream
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Event       import Schema__Logs__Event
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Events__Response import Schema__Logs__Events__Response
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Result    import Schema__Logs__Query__Result
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Row       import Schema__Logs__Query__Row


class Logs__AWS__Client(Type_Safe):
    region : str = ''                                                             # override to target specific region

    def client(self):                                                             # single boto3 seam — subclass overrides to inject fake
        kwargs = {}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.client('logs', **kwargs)

    # ── filter events ─────────────────────────────────────────────────────────

    def filter_events(self,
                      log_group      : str,
                      start_time     : int,
                      end_time       : int   = None,
                      filter_pattern : str   = '',
                      log_streams    : list  = None,
                      limit          : int   = 100,
                      ) -> Schema__Logs__Events__Response:
        kwargs = {
            'logGroupName' : log_group,
            'startTime'    : start_time,
            'limit'        : limit,
        }
        if end_time:
            kwargs['endTime'] = end_time
        if filter_pattern:
            kwargs['filterPattern'] = filter_pattern
        if log_streams:
            kwargs['logStreamNames'] = log_streams
        try:
            resp = self.client().filter_log_events(**kwargs)
        except Exception as e:
            return Schema__Logs__Events__Response()
        events = []
        for ev in resp.get('events', []):
            events.append(Schema__Logs__Event(
                event_id   = ev.get('eventId', ''),
                timestamp  = ev.get('timestamp', 0),
                log_stream = Safe_Str__Log__Stream(ev.get('logStreamName', '') if self._valid_stream(ev.get('logStreamName', '')) else ''),
                message    = ev.get('message', ''),
            ))
        return Schema__Logs__Events__Response(
            events           = events,
            searched_streams = len(resp.get('searchedLogStreams', [])),
            more_available   = bool(resp.get('nextToken')),
        )

    def tail_events(self,
                    log_group      : str,
                    filter_pattern : str = '',
                    poll_interval_ms: int = 2000,
                    ):                                                            # generator; caller breaks on Ctrl-C / StopIteration
        seen_ids = set()
        last_ts  = int(time.time() * 1000) - 5000                                # start 5s back to catch in-flight events
        while True:
            resp = self.filter_events(
                log_group      = log_group,
                start_time     = last_ts,
                filter_pattern = filter_pattern,
                limit          = 100,
            )
            for ev in resp.events:
                if ev.event_id not in seen_ids:
                    seen_ids.add(ev.event_id)
                    if ev.timestamp > last_ts:
                        last_ts = ev.timestamp
                    yield ev
            time.sleep(poll_interval_ms / 1000.0)

    # ── Insights queries ──────────────────────────────────────────────────────

    def start_query(self, log_group: str, query: str, start_time: int, end_time: int) -> str:
        resp = self.client().start_query(
            logGroupName = log_group,
            startTime    = start_time // 1000,                                    # Insights uses epoch seconds
            endTime      = end_time   // 1000,
            queryString  = query,
        )
        return resp['queryId']

    def get_query_results(self, query_id: str) -> Schema__Logs__Query__Result:
        resp   = self.client().get_query_results(queryId=query_id)
        status = resp.get('status', '')
        rows   = []
        for raw_row in resp.get('results', []):
            row_fields = {item['field']: item['value'] for item in raw_row}
            rows.append(Schema__Logs__Query__Row(fields=row_fields))
        return Schema__Logs__Query__Result(
            query_id = query_id,
            status   = status,
            rows     = rows,
        )

    def wait_query(self, query_id: str, timeout_sec: int = 30) -> Schema__Logs__Query__Result:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            result = self.get_query_results(query_id)
            if result.status != 'Running':
                return result
            time.sleep(0.5)
        return Schema__Logs__Query__Result(query_id=query_id, status='Timeout')

    # ── internal ──────────────────────────────────────────────────────────────

    def _valid_stream(self, s: str) -> bool:
        import re
        return bool(s) and bool(re.match(r'^[\w\-\.\[\]/:$ ]{1,512}$', s))
