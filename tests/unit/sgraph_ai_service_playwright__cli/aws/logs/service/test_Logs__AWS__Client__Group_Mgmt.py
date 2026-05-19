# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Logs__AWS__Client (group management methods)
# Covers: list_log_groups, describe_log_group, create_log_group,
#         delete_log_group, tail_log_group.
# No mocks, no patches. Uses Logs__AWS__Client__In_Memory.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.aws.logs.schemas.Schema__Logs__Group import Schema__Logs__Group
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory import Logs__AWS__Client__In_Memory

_NOW = int(time.time() * 1000)


class TestListLogGroups:

    def test_1__empty_returns_empty_list(self):
        client = Logs__AWS__Client__In_Memory()
        result = client.list_log_groups()
        assert result == []

    def test_2__returns_seeded_groups(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a')
        client.seed_group('/aws/ecs/my-service')
        result = client.list_log_groups()
        assert len(result) == 2

    def test_3__each_item_is_schema(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a', retention_days=14, stored_bytes=512)
        result = client.list_log_groups()
        assert len(result) == 1
        g = result[0]
        assert isinstance(g, Schema__Logs__Group)
        assert g.name           == '/aws/lambda/fn-a'
        assert g.retention_days == 14
        assert g.stored_bytes   == 512

    def test_4__prefix_filter_matches_prefix(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a')
        client.seed_group('/aws/ecs/svc')
        result = client.list_log_groups(prefix='/aws/lambda')
        assert len(result) == 1
        assert result[0].name == '/aws/lambda/fn-a'

    def test_5__prefix_filter_no_match(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-a')
        result = client.list_log_groups(prefix='/aws/ecs')
        assert result == []

    def test_6__retention_zero_when_no_policy(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/no-retention', retention_days=0)
        result = client.list_log_groups()
        assert result[0].retention_days == 0

    def test_7__never_raises_on_error(self):
        client = Logs__AWS__Client__In_Memory()
        # force exception path by passing bad state — method must still return []
        client._fake._groups_store = None   # causes iteration failure
        result = client.list_log_groups()
        assert result == []


class TestDescribeLogGroup:

    def test_8__returns_none_for_missing_group(self):
        client = Logs__AWS__Client__In_Memory()
        assert client.describe_log_group('/no-such-group') is None

    def test_9__returns_schema_for_existing_group(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-b', retention_days=30)
        result = client.describe_log_group('/aws/lambda/fn-b')
        assert result is not None
        assert isinstance(result, Schema__Logs__Group)
        assert result.name           == '/aws/lambda/fn-b'
        assert result.retention_days == 30

    def test_10__exact_match_not_prefix_match(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn')
        client.seed_group('/aws/lambda/fn-extra')
        # describe exact '/aws/lambda/fn' must not return '/aws/lambda/fn-extra'
        result = client.describe_log_group('/aws/lambda/fn')
        assert result is not None
        assert result.name == '/aws/lambda/fn'

    def test_11__returns_none_on_exception(self):
        client = Logs__AWS__Client__In_Memory()
        client._fake._groups_store = None
        result = client.describe_log_group('/boom')
        assert result is None


class TestCreateLogGroup:

    def test_12__creates_new_group(self):
        client = Logs__AWS__Client__In_Memory()
        ok = client.create_log_group('/my/group')
        assert ok is True
        assert client.describe_log_group('/my/group') is not None

    def test_13__sets_retention_policy(self):
        client = Logs__AWS__Client__In_Memory()
        client.create_log_group('/my/group', retention_days=14)
        g = client.describe_log_group('/my/group')
        assert g.retention_days == 14

    def test_14__idempotent_already_exists(self):
        client = Logs__AWS__Client__In_Memory()
        client.create_log_group('/my/group')
        ok = client.create_log_group('/my/group')            # second call must not raise
        assert ok is True

    def test_15__no_retention_when_retention_days_zero(self):
        client = Logs__AWS__Client__In_Memory()
        client.create_log_group('/my/group', retention_days=0)
        g = client.describe_log_group('/my/group')
        assert g.retention_days == 0                         # no policy set


class TestDeleteLogGroup:

    def test_16__delete_existing_group_returns_true(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-c')
        ok = client.delete_log_group('/aws/lambda/fn-c')
        assert ok is True
        assert client.describe_log_group('/aws/lambda/fn-c') is None

    def test_17__delete_missing_group_returns_false(self):
        client = Logs__AWS__Client__In_Memory()
        ok = client.delete_log_group('/no-such-group')
        assert ok is False

    def test_18__delete_is_idempotent_second_call_false(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_group('/aws/lambda/fn-d')
        client.delete_log_group('/aws/lambda/fn-d')
        ok = client.delete_log_group('/aws/lambda/fn-d')
        assert ok is False


class TestTailLogGroup:

    def test_19__returns_empty_when_no_events(self):
        client = Logs__AWS__Client__In_Memory()
        events = client.tail_log_group('/my/group')
        assert events == []

    def test_20__returns_events_within_window(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'stream/0', 'hello world', _NOW - 100)
        events = client.tail_log_group('/my/group', since_minutes=60)
        assert len(events) == 1
        assert events[0]['message']      == 'hello world'
        assert events[0]['stream']       == 'stream/0'
        assert 'timestamp_ms' in events[0]

    def test_21__excludes_events_outside_window(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'stream/0', 'old', _NOW - 9_000_000)   # >2h ago
        events = client.tail_log_group('/my/group', since_minutes=60)
        assert events == []

    def test_22__stream_prefix_filter(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'app/server',  'msg-a', _NOW - 100)
        client.seed_event('/my/group', 'app/worker',  'msg-b', _NOW - 100)
        client.seed_event('/my/group', 'other/thing', 'msg-c', _NOW - 100)
        events = client.tail_log_group('/my/group', stream_prefix='app/')
        assert len(events) == 2

    def test_23__max_events_respected(self):
        client = Logs__AWS__Client__In_Memory()
        for i in range(10):
            client.seed_event('/my/group', 'stream/0', f'msg {i}', _NOW - i * 10)
        events = client.tail_log_group('/my/group', max_events=5)
        assert len(events) == 5

    def test_24__follow_false_returns_list(self):
        client = Logs__AWS__Client__In_Memory()
        client.seed_event('/my/group', 'stream/0', 'test', _NOW - 50)
        events = client.tail_log_group('/my/group', follow=False)
        assert isinstance(events, list)
