# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Logs__AWS__Client
# CloudWatch Logs access: log group management, filter events, Insights queries.
#
# EXCEPTION — boto3 used directly. osbot_aws does not cover FilterLogEvents,
# StartQuery, GetQueryResults, or log group CRUD at the level needed here.
# This module is the sole boto3 boundary for CloudWatch Logs — subclasses
# override client() to inject fakes for tests.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing import Optional

import boto3                                                                      # EXCEPTION — see module header
from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.logs.primitives.Safe_Str__Log__Stream import Safe_Str__Log__Stream
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Event       import Schema__Logs__Event
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Events__Response import Schema__Logs__Events__Response
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Group            import Schema__Logs__Group
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Result    import Schema__Logs__Query__Result
from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Query__Row       import Schema__Logs__Query__Row


class Logs__AWS__Client(Type_Safe):
    region : str = ''                                                             # override to target specific region

    def client(self):                                                             # single boto3 seam — subclass overrides to inject fake
        kwargs = {}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.client('logs', **kwargs)

    # ── log group management ──────────────────────────────────────────────────

    def list_log_groups(self, prefix: str = '') -> list:                          # returns list[Schema__Logs__Group]; never raises
        try:
            logs   = self.client()
            kwargs = {}
            if prefix:
                kwargs['logGroupNamePrefix'] = prefix
            paginator = logs.get_paginator('describe_log_groups')
            result    = []
            for page in paginator.paginate(**kwargs):
                for raw in page.get('logGroups', []):
                    result.append(self._parse_group(raw))
            return result
        except Exception:
            return []

    def describe_log_group(self, name: str) -> Optional[Schema__Logs__Group]:   # exact-match on name; None if not found
        try:
            logs = self.client()
            resp = logs.describe_log_groups(logGroupNamePrefix=name)
            for raw in resp.get('logGroups', []):
                if raw.get('logGroupName') == name:
                    return self._parse_group(raw)
            return None
        except Exception:
            return None

    def create_log_group(self, name: str, retention_days: int = 7) -> bool:      # idempotent — ResourceAlreadyExistsException → True
        try:
            self.client().create_log_group(logGroupName=name)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code != 'ResourceAlreadyExistsException':
                raise
        if retention_days > 0:
            try:
                self.client().put_retention_policy(logGroupName=name,
                                                   retentionInDays=retention_days)
            except Exception:
                pass
        return True

    def update_retention(self, name: str, days: int) -> bool:                    # suppresses ResourceNotFoundException → False
        try:
            self.client().put_retention_policy(logGroupName=name, retentionInDays=days)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'ResourceNotFoundException':
                return False
            raise

    def delete_log_group(self, name: str) -> bool:                               # suppresses ResourceNotFoundException → False
        try:
            self.client().delete_log_group(logGroupName=name)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'ResourceNotFoundException':
                return False
            raise

    def tail_log_group(self, name: str, stream_prefix: str = '',
                       since_minutes: int = 60, follow: bool = False,
                       max_events: int = 200) -> list:                            # follow=True is for CLI use; tests always use follow=False
        start_time = int(time.time() * 1000) - since_minutes * 60 * 1000
        kwargs = dict(logGroupName=name, startTime=start_time,
                      filterPattern='', limit=max_events)
        if stream_prefix:
            kwargs['logStreamNamePrefix'] = stream_prefix
        try:
            resp   = self.client().filter_log_events(**kwargs)
            events = resp.get('events', [])
            result = [dict(timestamp_ms=ev.get('timestamp', 0),
                           stream=ev.get('logStreamName', ''),
                           message=ev.get('message', ''))
                      for ev in events]
        except Exception:
            result = []
        if follow:
            pass                                                                  # follow mode: caller wraps in loop; method returns batch for tests
        return result

    # ── internal: parse ───────────────────────────────────────────────────────

    def _parse_group(self, raw: dict) -> Schema__Logs__Group:
        return Schema__Logs__Group(
            name           = raw.get('logGroupName',    '') or '',
            retention_days = int(raw.get('retentionInDays', 0) or 0),
            arn            = raw.get('logGroupArn',     '') or '',
            stored_bytes   = int(raw.get('storedBytes', 0) or 0),
        )

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
