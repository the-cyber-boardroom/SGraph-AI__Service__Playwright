# ═══════════════════════════════════════════════════════════════════════════════
# Tests — CloudTrail__AWS__Client (in-memory)
# Unit tests for lookup_events / get_event / list_trails / describe_trail.
# No mocks. No patches. Uses CloudTrail__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.cloudtrail.schemas.Schema__CloudTrail__Event import Schema__CloudTrail__Event
from sgraph_ai_service_playwright__cli.aws.cloudtrail.schemas.Schema__CloudTrail__Trail import Schema__CloudTrail__Trail
from tests.unit.sgraph_ai_service_playwright__cli.aws.cloudtrail.service.CloudTrail__AWS__Client__In_Memory import CloudTrail__AWS__Client__In_Memory


def _client() -> CloudTrail__AWS__Client__In_Memory:
    return CloudTrail__AWS__Client__In_Memory()


class Test__CloudTrail__AWS__Client:

    def test_1__lookup_events_empty(self):
        result = _client().lookup_events()
        assert len(result) == 0

    def test_2__lookup_events_returns_seeded_event(self):
        c   = _client()
        eid = c.seed_event(event_name='PutObject', username='alice')
        result = c.lookup_events()
        assert len(result) == 1
        ev = result[0]
        assert isinstance(ev, Schema__CloudTrail__Event)
        assert ev.event_id   == eid
        assert ev.event_name == 'PutObject'
        assert ev.username   == 'alice'

    def test_3__lookup_events_filter_by_action(self):
        c = _client()
        c.seed_event(event_name='PutObject')
        c.seed_event(event_name='GetObject')
        c.seed_event(event_name='DeleteObject')
        result = c.lookup_events(action='GetObject')
        assert len(result) == 1
        assert result[0].event_name == 'GetObject'

    def test_4__lookup_events_filter_by_user(self):
        c = _client()
        c.seed_event(username='alice')
        c.seed_event(username='bob')
        c.seed_event(username='alice')
        result = c.lookup_events(user='alice')
        assert len(result) == 2
        assert all(e.username == 'alice' for e in result)

    def test_5__lookup_events_limit(self):
        c = _client()
        for i in range(10):
            c.seed_event(event_name=f'Event{i}')
        result = c.lookup_events(limit=3)
        assert len(result) == 3

    def test_6__lookup_events_source_ip_and_region_parsed(self):
        c = _client()
        c.seed_event(source_ip='10.0.0.1', aws_region='eu-west-1')
        result = c.lookup_events()
        ev = result[0]
        assert ev.source_ip_address == '10.0.0.1'
        assert ev.aws_region        == 'eu-west-1'

    def test_7__lookup_events_error_fields_parsed(self):
        c = _client()
        c.seed_event(error_code='AccessDenied', error_message='Access denied')
        result = c.lookup_events()
        ev = result[0]
        assert ev.error_code    == 'AccessDenied'
        assert ev.error_message == 'Access denied'

    def test_8__get_event_by_id(self):
        c   = _client()
        eid = c.seed_event(event_name='CreateBucket')
        ev  = c.get_event(eid)
        assert ev is not None
        assert ev.event_id   == eid
        assert ev.event_name == 'CreateBucket'

    def test_9__get_event_missing_returns_none(self):
        c  = _client()
        ev = c.get_event('00000000-0000-0000-0000-000000000000')
        assert ev is None

    def test_10__list_trails_empty(self):
        result = _client().list_trails()
        assert len(result) == 0

    def test_11__list_trails_returns_seeded_trail(self):
        c = _client()
        c.seed_trail(name='prod-trail', s3_bucket='prod-logs', home_region='us-east-1')
        result = c.list_trails()
        assert len(result) == 1
        tr = result[0]
        assert isinstance(tr, Schema__CloudTrail__Trail)
        assert tr.name           == 'prod-trail'
        assert tr.s3_bucket_name == 'prod-logs'
        assert tr.home_region    == 'us-east-1'

    def test_12__list_trails_is_logging_flag(self):
        c = _client()
        c.seed_trail(name='active-trail',  is_logging=True)
        c.seed_trail(name='stopped-trail', is_logging=False)
        result = c.list_trails()
        by_name = {tr.name: tr for tr in result}
        assert by_name['active-trail'].is_logging  is True
        assert by_name['stopped-trail'].is_logging is False

    def test_13__describe_trail_existing(self):
        c = _client()
        c.seed_trail(name='my-trail', multi_region=True, include_global=True,
                     log_validation=True, is_logging=True)
        tr = c.describe_trail('my-trail')
        assert tr is not None
        assert tr.name                         == 'my-trail'
        assert tr.is_multi_region_trail        is True
        assert tr.include_global_service_events is True
        assert tr.log_file_validation_enabled  is True
        assert tr.is_logging                   is True
        assert 'arn:aws:cloudtrail' in tr.trail_arn

    def test_14__describe_trail_missing_returns_none(self):
        c  = _client()
        tr = c.describe_trail('no-such-trail')
        assert tr is None

    def test_15__multiple_events_order_preserved(self):
        c    = _client()
        ids  = [c.seed_event(event_name=f'Action{i}') for i in range(5)]
        result = c.lookup_events(limit=5)
        assert len(result) == 5
        assert [e.event_id for e in result] == ids
