# ═══════════════════════════════════════════════════════════════════════════════
# tests — Event__Bus
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus import Event__Bus, event_bus


class test_Event__Bus(TestCase):

    def setUp(self):
        event_bus.reset()

    # ── type-safe construction ───────────────────────────────────────────────

    def test__init__listeners_is_empty_dict(self):
        bus = Event__Bus()
        assert bus.listeners == {}

    # ── emit ────────────────────────────────────────────────────────────────

    def test__emit_with_no_listener__silently_drops__returns_zero(self):
        delivered = event_bus.emit('test:nothing.happened', {})
        assert delivered == 0

    def test__emit_with_one_listener__delivers__returns_one(self):
        received = []
        event_bus.on('test:thing.happened', lambda p: received.append(p))
        delivered = event_bus.emit('test:thing.happened', {'a': 1})
        assert delivered == 1
        assert received  == [{'a': 1}]

    def test__emit_with_multiple_listeners__all_invoked(self):
        got_a, got_b = [], []
        event_bus.on('test:multi', lambda p: got_a.append(p))
        event_bus.on('test:multi', lambda p: got_b.append(p))
        delivered = event_bus.emit('test:multi', 'x')
        assert delivered == 2
        assert got_a     == ['x']
        assert got_b     == ['x']

    def test__emit__listener_exception__caught__other_listeners_still_invoked(self):
        def bad_handler(_): raise ValueError('boom')
        good_got = []
        event_bus.on('test:x.happened', bad_handler)
        event_bus.on('test:x.happened', lambda p: good_got.append(p))
        delivered = event_bus.emit('test:x.happened', 'hi')
        assert delivered == 1                                                   # only the good handler counted
        assert good_got  == ['hi']

    def test__emit__returns_count_of_successful_deliveries_only(self):
        def always_raise(_): raise RuntimeError
        event_bus.on('ev', always_raise)
        event_bus.on('ev', always_raise)
        assert event_bus.emit('ev', {}) == 0

    # ── on / off ────────────────────────────────────────────────────────────

    def test__on__returns_handler_for_storage(self):
        handler = lambda p: p
        result  = event_bus.on('test:reg', handler)
        assert result is handler

    def test__off__removes_listener__returns_true(self):
        handler = lambda p: p
        event_bus.on('test:ev', handler)
        removed = event_bus.off('test:ev', handler)
        assert removed                           is True
        assert event_bus.listener_count('test:ev') == 0

    def test__off__handler_not_registered__returns_false(self):
        result = event_bus.off('test:ev', lambda p: p)
        assert result is False

    # ── listener_count ───────────────────────────────────────────────────────

    def test__listener_count__no_listeners__returns_zero(self):
        assert event_bus.listener_count('test:absent') == 0

    def test__listener_count__after_on__returns_correct_count(self):
        event_bus.on('test:c', lambda p: p)
        event_bus.on('test:c', lambda p: p)
        assert event_bus.listener_count('test:c') == 2

    # ── reset ────────────────────────────────────────────────────────────────

    def test__reset__clears_all_listeners(self):
        event_bus.on('test:a', lambda p: p)
        event_bus.on('test:b', lambda p: p)
        event_bus.reset()
        assert event_bus.listeners == {}

    # ── module-level singleton ───────────────────────────────────────────────

    def test__module_singleton__is_Event__Bus_instance(self):
        assert isinstance(event_bus, Event__Bus)

    def test__module_singleton__shared_state_across_imports(self):
        from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus import event_bus as bus2
        assert event_bus is bus2
