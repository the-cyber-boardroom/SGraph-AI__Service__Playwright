# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Agentic_Boot_State (v0.1.29)
#
# Module-level ring buffer + last-error holder. Lives in L1 so the admin API
# can read it without depending on L2 (Agentic_Boot_Shim).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright.agentic_fastapi.Agentic_Boot_State                import (BOOT_LOG_MAX_LINES,
                                                                                            append_boot_log   ,
                                                                                            get_boot_log      ,
                                                                                            get_last_error    ,
                                                                                            reset_boot_state  ,
                                                                                            set_last_error    )


class test_boot_log(TestCase):

    def setUp(self):
        reset_boot_state()

    def test__append_and_read_are_symmetric(self):
        append_boot_log('hello')
        append_boot_log('world')
        assert get_boot_log() == ['hello', 'world']

    def test__get_returns_a_copy(self):                                             # Callers must never be able to mutate the buffer
        append_boot_log('line-1')
        snapshot = get_boot_log()
        snapshot.append('mutation')
        assert get_boot_log() == ['line-1']

    def test__ring_buffer_drops_oldest(self):
        for i in range(BOOT_LOG_MAX_LINES + 10):                                    # Overflow the ring by 10
            append_boot_log(f'line-{i}')
        log = get_boot_log()
        assert len(log)   == BOOT_LOG_MAX_LINES
        assert log[0]     == f'line-10'                                             # First 10 were discarded
        assert log[-1]    == f'line-{BOOT_LOG_MAX_LINES + 9}'


class test_last_error(TestCase):

    def setUp(self):
        reset_boot_state()

    def test__defaults_to_empty(self):
        assert get_last_error() == ''

    def test__set_and_get(self):
        set_last_error('boom')
        assert get_last_error() == 'boom'

    def test__set_none_becomes_empty_string(self):                                  # Helpers like this catch a whole class of "error was falsy" bugs
        set_last_error(None)
        assert get_last_error() == ''

    def test__reset_clears_both(self):
        append_boot_log('line')
        set_last_error('boom')
        reset_boot_state()
        assert get_boot_log()   == []
        assert get_last_error() == ''
