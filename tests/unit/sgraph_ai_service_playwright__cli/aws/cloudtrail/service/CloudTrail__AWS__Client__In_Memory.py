# ═══════════════════════════════════════════════════════════════════════════════
# Tests — CloudTrail__AWS__Client__In_Memory
# Dict-backed fake boto3 CloudTrail client for unit tests. No mocks. No patches.
# Supports lookup_events, list_trails, describe_trails, get_trail_status.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import uuid
from datetime import datetime, timezone

from sgraph_ai_service_playwright__cli.aws.cloudtrail.service.CloudTrail__AWS__Client import CloudTrail__AWS__Client


class _Fake_CloudTrail_Client:                                                   # Minimal boto3-alike CloudTrail client backed by in-memory dicts

    def __init__(self, events: list, trails: dict, statuses: dict):
        self._events   = events    # list of raw event dicts
        self._trails   = trails    # trail_name → raw trail dict
        self._statuses = statuses  # trail_name → status dict

    # ── events ────────────────────────────────────────────────────────────────

    def lookup_events(self, StartTime=None, EndTime=None, LookupAttributes=None,
                      MaxResults=50, NextToken=None, **_):
        events = list(self._events)
        if StartTime:
            events = [e for e in events
                      if self._event_time(e) >= StartTime]
        if LookupAttributes:
            attr = LookupAttributes[0]
            key  = attr.get('AttributeKey', '')
            val  = attr.get('AttributeValue', '')
            if key == 'EventName':
                events = [e for e in events if e.get('EventName', '') == val]
            elif key == 'Username':
                events = [e for e in events if e.get('Username', '') == val]
            elif key == 'EventSource':
                ct_rec = lambda e: json.loads(e.get('CloudTrailEvent', '{}'))
                events = [e for e in events
                          if ct_rec(e).get('eventSource', '') == val]
        # pagination: NextToken is just a start-index string
        start = int(NextToken) if NextToken else 0
        page  = events[start: start + MaxResults]
        next_tok = str(start + MaxResults) if (start + MaxResults) < len(events) else None
        result = {'Events': page}
        if next_tok:
            result['NextToken'] = next_tok
        return result

    # ── trails ────────────────────────────────────────────────────────────────

    def list_trails(self, **_):
        return {'Trails': [dict(
            Name                      = tr['Name'],
            TrailARN                  = tr.get('TrailARN', ''),
            HomeRegion                = tr.get('HomeRegion', 'us-east-1'),
            S3BucketName              = tr.get('S3BucketName', ''),
            IsMultiRegionTrail        = tr.get('IsMultiRegionTrail', False),
            IncludeGlobalServiceEvents= tr.get('IncludeGlobalServiceEvents', False),
            LogFileValidationEnabled  = tr.get('LogFileValidationEnabled', False),
        ) for tr in self._trails.values()]}

    def describe_trails(self, trailNameList=None, includeShadowTrails=True, **_):
        result = []
        for name in (trailNameList or []):
            raw = self._trails.get(name)
            if raw:
                result.append(raw)
        return {'trailList': result}

    def get_trail_status(self, Name='', **_):
        return self._statuses.get(Name, {'IsLogging': False})

    # ── helpers ───────────────────────────────────────────────────────────────

    def _event_time(self, raw: dict):
        et = raw.get('EventTime')
        if isinstance(et, datetime):
            return et
        return datetime.min.replace(tzinfo=timezone.utc)


class CloudTrail__AWS__Client__In_Memory(CloudTrail__AWS__Client):

    def __init__(self):
        super().__init__()
        self._events   = []
        self._trails   = {}
        self._statuses = {}
        self._fake     = _Fake_CloudTrail_Client(self._events, self._trails, self._statuses)

    def client(self):
        return self._fake

    # ── seed helpers ──────────────────────────────────────────────────────────

    def seed_event(self, event_name: str = 'PutObject',
                   username: str = 'alice',
                   source_ip: str = '1.2.3.4',
                   aws_region: str = 'us-east-1',
                   event_source: str = 's3.amazonaws.com',
                   error_code: str = '',
                   error_message: str = '') -> str:
        event_id  = str(uuid.uuid4())
        ct_record = json.dumps({
            'eventVersion'   : '1.08',
            'eventSource'    : event_source,
            'awsRegion'      : aws_region,
            'sourceIPAddress': source_ip,
            'requestParameters' : {'bucketName': 'my-bucket'},
            'responseElements'  : None,
            'errorCode'      : error_code,
            'errorMessage'   : error_message,
        })
        raw = {
            'EventId'         : event_id,
            'EventName'       : event_name,
            'Username'        : username,
            'EventTime'       : datetime.now(timezone.utc),
            'CloudTrailEvent' : ct_record,
            'Resources'       : [],
        }
        self._events.append(raw)
        return event_id

    def seed_trail(self, name: str = 'my-trail',
                   s3_bucket: str = 'my-logs-bucket',
                   home_region: str = 'us-east-1',
                   multi_region: bool = True,
                   include_global: bool = True,
                   log_validation: bool = True,
                   is_logging: bool = True) -> None:
        arn = f'arn:aws:cloudtrail:{home_region}:123456789012:trail/{name}'
        self._trails[name] = {
            'Name'                      : name,
            'TrailARN'                  : arn,
            'S3BucketName'              : s3_bucket,
            'HomeRegion'                : home_region,
            'IsMultiRegionTrail'        : multi_region,
            'IncludeGlobalServiceEvents': include_global,
            'LogFileValidationEnabled'  : log_validation,
        }
        self._statuses[name] = {'IsLogging': is_logging}
