# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — CloudTrail__AWS__Client
# Thin boto3 boundary for CloudTrail lookup_events, list_trails, describe_trail,
# and get_trail_status.  All operations are read-only — no mutation gate needed.
#
# EXCEPTION — boto3 used directly.  osbot_aws does not expose a CloudTrail
# wrapper at the level needed here.  This module is the single CloudTrail boto3
# seam; subclasses override client() to inject fakes for unit tests.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import re
import time
from datetime  import datetime, timezone
from typing    import Optional

import boto3                                                                      # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cloudtrail.collections.List__Schema__CloudTrail__Event import List__Schema__CloudTrail__Event
from sgraph_ai_service_playwright__cli.aws.cloudtrail.collections.List__Schema__CloudTrail__Trail import List__Schema__CloudTrail__Trail
from sgraph_ai_service_playwright__cli.aws.cloudtrail.schemas.Schema__CloudTrail__Event           import Schema__CloudTrail__Event
from sgraph_ai_service_playwright__cli.aws.cloudtrail.schemas.Schema__CloudTrail__Trail           import Schema__CloudTrail__Trail


_RELATIVE = re.compile(r'^(\d+)(s|m|h|d)$')
_UNIT_S   = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}


class CloudTrail__AWS__Client(Type_Safe):

    def client(self):                                                             # single boto3 seam — subclass overrides for tests
        return boto3.client('cloudtrail')

    # ── read ──────────────────────────────────────────────────────────────────

    def lookup_events(self,
                      user    : str = '',
                      service : str = '',
                      action  : str = '',
                      since   : str = '1h',
                      limit   : int = 100) -> List__Schema__CloudTrail__Event:
        ct          = self.client()
        start_time  = self._parse_since(since)
        lookup_attr = self._build_lookup_attribute(user, service, action)
        kwargs      = {
            'StartTime' : start_time,
            'MaxResults': min(limit, 50),               # CloudTrail max per page is 50
        }
        if lookup_attr:
            kwargs['LookupAttributes'] = [lookup_attr]
        result  = List__Schema__CloudTrail__Event()
        fetched = 0
        while fetched < limit:
            resp        = ct.lookup_events(**kwargs)
            events      = resp.get('Events', [])
            for raw in events:
                if fetched >= limit:
                    break
                result.append(self._parse_event(raw))
                fetched += 1
            next_token  = resp.get('NextToken')
            if not next_token or not events:
                break
            kwargs['NextToken']  = next_token
            kwargs['MaxResults'] = min(limit - fetched, 50)
        return result

    def get_event(self, event_id: str) -> Optional[Schema__CloudTrail__Event]:  # searches recent 24h for the event_id
        ct = self.client()
        start_time = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc)
        kwargs = {'StartTime': start_time, 'MaxResults': 50}
        while True:
            resp = ct.lookup_events(**kwargs)
            for raw in resp.get('Events', []):
                if raw.get('EventId', '') == event_id:
                    return self._parse_event(raw)
            next_token = resp.get('NextToken')
            if not next_token:
                break
            kwargs['NextToken'] = next_token
        return None

    def list_trails(self) -> List__Schema__CloudTrail__Trail:
        ct   = self.client()
        resp = ct.list_trails()
        result = List__Schema__CloudTrail__Trail()
        for item in resp.get('Trails', []):
            trail = self._parse_trail_summary(item, ct)
            result.append(trail)
        return result

    def describe_trail(self, name: str) -> Optional[Schema__CloudTrail__Trail]:
        try:
            ct   = self.client()
            resp = ct.describe_trails(trailNameList=[name], includeShadowTrails=False)
            trails = resp.get('trailList', [])
            if not trails:
                return None
            raw    = trails[0]
            status = {}
            try:
                status = ct.get_trail_status(Name=name)
            except Exception:
                pass
            return self._parse_trail_full(raw, status)
        except Exception:
            return None

    def get_trail_status(self, name: str) -> dict:
        try:
            return self.client().get_trail_status(Name=name)
        except Exception:
            return {}

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_since(self, expr: str) -> datetime:                               # returns aware datetime for the start of the window
        expr = (expr or '1h').strip()
        m    = _RELATIVE.match(expr)
        if m:
            amount = int(m.group(1))
            unit   = m.group(2)
            secs   = amount * _UNIT_S[unit]
            return datetime.fromtimestamp(time.time() - secs, tz=timezone.utc)
        try:
            if expr.endswith('Z'):
                expr = expr[:-1]
            dt = datetime.fromisoformat(expr)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.fromtimestamp(time.time() - 3600, tz=timezone.utc)  # fallback: 1h ago

    def _build_lookup_attribute(self, user: str, service: str,
                                action: str) -> Optional[dict]:                  # CloudTrail only supports one LookupAttribute at a time
        if action:
            return {'AttributeKey': 'EventName', 'AttributeValue': action}
        if user:
            return {'AttributeKey': 'Username', 'AttributeValue': user}
        if service:
            return {'AttributeKey': 'EventSource', 'AttributeValue': service}
        return None

    def _parse_event(self, raw: dict) -> Schema__CloudTrail__Event:
        ct_record = {}
        if raw.get('CloudTrailEvent'):
            try:
                ct_record = json.loads(raw['CloudTrailEvent'])
            except Exception:
                pass
        event_time = raw.get('EventTime')
        time_str   = str(event_time) if event_time else ''
        resources  = raw.get('Resources', [])
        return Schema__CloudTrail__Event(
            event_id           = raw.get('EventId', ''),
            event_time         = time_str,
            event_name         = raw.get('EventName', ''),
            username           = raw.get('Username', ''),
            source_ip_address  = ct_record.get('sourceIPAddress', ''),
            aws_region         = ct_record.get('awsRegion', ''),
            request_parameters = json.dumps(ct_record.get('requestParameters') or {}),
            response_elements  = json.dumps(ct_record.get('responseElements') or {}),
            resources          = json.dumps(resources),
            error_code         = ct_record.get('errorCode', ''),
            error_message      = ct_record.get('errorMessage', ''),
        )

    def _parse_trail_summary(self, item: dict, ct) -> Schema__CloudTrail__Trail:
        name   = item.get('Name', '') or item.get('TrailARN', '').split('/')[-1]
        is_log = False
        try:
            status = ct.get_trail_status(Name=name)
            is_log = bool(status.get('IsLogging', False))
        except Exception:
            pass
        return Schema__CloudTrail__Trail(
            name                         = name,
            s3_bucket_name               = item.get('S3BucketName', ''),
            home_region                  = item.get('HomeRegion', ''),
            is_multi_region_trail        = bool(item.get('IsMultiRegionTrail', False)),
            include_global_service_events= bool(item.get('IncludeGlobalServiceEvents', False)),
            log_file_validation_enabled  = bool(item.get('LogFileValidationEnabled', False)),
            trail_arn                    = item.get('TrailARN', ''),
            is_logging                   = is_log,
        )

    def _parse_trail_full(self, raw: dict, status: dict) -> Schema__CloudTrail__Trail:
        name = raw.get('Name', '') or raw.get('TrailARN', '').split('/')[-1]
        return Schema__CloudTrail__Trail(
            name                         = name,
            s3_bucket_name               = raw.get('S3BucketName', ''),
            home_region                  = raw.get('HomeRegion', ''),
            is_multi_region_trail        = bool(raw.get('IsMultiRegionTrail', False)),
            include_global_service_events= bool(raw.get('IncludeGlobalServiceEvents', False)),
            log_file_validation_enabled  = bool(raw.get('LogFileValidationEnabled', False)),
            trail_arn                    = raw.get('TrailARN', ''),
            is_logging                   = bool(status.get('IsLogging', False)),
        )
