# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Instance__Manager (no mocks, no patches)
# The state machine, idempotency and idle-timer arming — exercised in-memory
# exactly as they will run against AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Instance__State import Enum__Instance__State
from vault_publish.schemas.Safe_Str__Slug        import Safe_Str__Slug
from vault_publish.service.Instance__Manager     import Instance__Manager

SLUG = Safe_Str__Slug('sara-cv')


class test_Instance__Manager(TestCase):

    def setUp(self):
        self.manager = Instance__Manager()

    def test_unknown_slug_state_is_unknown(self):
        assert self.manager.state(SLUG) == Enum__Instance__State.UNKNOWN

    def test_start_transitions_to_pending(self):
        record, was_running = self.manager.start(SLUG)
        assert was_running         is False
        assert record.state        == Enum__Instance__State.PENDING
        assert str(record.instance_id) != ''
        assert record.idle_timer_armed is True

    def test_mark_ready_transitions_to_running(self):
        self.manager.start(SLUG)
        record = self.manager.mark_ready(SLUG)
        assert record.state == Enum__Instance__State.RUNNING

    def test_start_when_running_is_idempotent(self):
        self.manager.start(SLUG)
        self.manager.mark_ready(SLUG)
        record, was_running = self.manager.start(SLUG)
        assert was_running  is True
        assert record.state == Enum__Instance__State.RUNNING

    def test_start_keeps_same_instance_id(self):
        record_a, _ = self.manager.start(SLUG)
        self.manager.mark_ready(SLUG)
        record_b, _ = self.manager.start(SLUG)
        assert str(record_a.instance_id) == str(record_b.instance_id)

    def test_stop_transitions_to_stopped_and_disarms_timer(self):
        self.manager.start(SLUG)
        record = self.manager.stop(SLUG)
        assert record.state            == Enum__Instance__State.STOPPED
        assert record.idle_timer_armed is False

    def test_distinct_slugs_have_distinct_instance_ids(self):
        record_a, _ = self.manager.start(Safe_Str__Slug('slug-a'))
        record_b, _ = self.manager.start(Safe_Str__Slug('slug-b'))
        assert str(record_a.instance_id) != str(record_b.instance_id)
