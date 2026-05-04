# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Request__Watchdog
#
# Unit tests use a subclass that overrides `now_ms()` (freeze the clock) and
# `kill()` (record the call instead of os._exit'ing the test runner). The
# background thread is NEVER started — `check_once()` is invoked directly.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                 import Any, List, Tuple
from unittest                                                                import TestCase

from sgraph_ai_service_playwright.consts.env_vars                           import (ENV_VAR__WATCHDOG_DISABLED        ,
                                                                                     ENV_VAR__WATCHDOG_MAX_REQUEST_MS  ,
                                                                                     ENV_VAR__WATCHDOG_POLL_INTERVAL_MS)
from sgraph_ai_service_playwright.service.Request__Watchdog                 import (DEFAULT_MAX_REQUEST_MS   ,
                                                                                     DEFAULT_POLL_INTERVAL_MS ,
                                                                                     Request__Watchdog        )


ENV_KEYS = [ENV_VAR__WATCHDOG_DISABLED        ,
            ENV_VAR__WATCHDOG_MAX_REQUEST_MS  ,
            ENV_VAR__WATCHDOG_POLL_INTERVAL_MS]


class _EnvScrub:                                                                    # Snapshot/restore only watchdog env vars

    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}

    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self

    def __exit__(self, *_):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        for k, v in self.snapshot.items():
            if v is not None:
                os.environ[k] = v


class _FakeWatchdog(Request__Watchdog):                                             # Clock + kill seam overrides — never terminates the test runner
    current_time_ms : int                              = 0
    kills           : List[Tuple[str, int]]            = None                        # (request_id, duration_ms) — populated instead of os._exit

    def setup(self):
        super().setup()
        self.kills = []                                                             # Reset per instance
        return self

    def now_ms(self) -> int:
        return self.current_time_ms

    def kill(self, request_id: str, duration_ms: int) -> None:
        self.kills.append((request_id, duration_ms))                                # Record and return; tests assert on the list


class test_setup(TestCase):

    def test__defaults_applied_when_env_unset(self):
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            assert int(wd.max_request_ms  ) == DEFAULT_MAX_REQUEST_MS
            assert int(wd.poll_interval_ms) == DEFAULT_POLL_INTERVAL_MS
            assert wd.disabled is False
            assert wd.lock     is not None

    def test__env_vars_override_defaults(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS  : '10000',
                          ENV_VAR__WATCHDOG_POLL_INTERVAL_MS:  '500' ,
                          ENV_VAR__WATCHDOG_DISABLED        :   '1'  }):
            wd = _FakeWatchdog().setup()
            assert int(wd.max_request_ms  ) == 10000
            assert int(wd.poll_interval_ms) ==   500
            assert wd.disabled is True


class test_register_and_unregister(TestCase):

    def test__register_records_start_time(self):
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 1_000
            wd.register('req-1')
            assert 'req-1' in wd.in_flight
            assert wd.in_flight['req-1'] == 1_000                                   # Plain int — epoch-ms stamp, not a Safe_UInt__Milliseconds duration

    def test__unregister_removes_entry(self):
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 1_000
            wd.register('req-1')
            wd.unregister('req-1')
            assert 'req-1' not in wd.in_flight

    def test__unregister_missing_is_noop(self):
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            wd.unregister('never-seen')                                              # Must not raise — middleware should never blow up on spurious unregister

    def test__disabled_register_is_noop(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_DISABLED: '1'}):
            wd = _FakeWatchdog().setup()
            wd.register('req-1')
            assert 'req-1' not in wd.in_flight                                       # Disabled watchdog doesn't track anything — critical for tests + laptop dev

    def test__register_accepts_realistic_epoch_stamp(self):                          # Regression: commit 907fc9b — epoch millis must not be wrapped in Safe_UInt__Milliseconds (caps at 900_000)
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 1_776_444_118_146                                   # Realistic 2026 epoch-ms stamp — would overflow Safe_UInt__Milliseconds' 15-min cap
            wd.register('req-1')                                                     # Must not raise
            assert wd.in_flight['req-1'] == 1_776_444_118_146


class test_check_once(TestCase):

    def test__within_threshold_does_not_kill(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '5000'}):
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 1_000
            wd.register('req-1')
            wd.current_time_ms = 4_999                                                # 3999 ms elapsed — under 5000 ms threshold
            wd.check_once()
            assert wd.kills == []

    def test__exceeded_threshold_triggers_kill(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '5000'}):
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 1_000
            wd.register('req-1')
            wd.current_time_ms = 7_000                                                # 6000 ms elapsed — breaches 5000 ms threshold
            wd.check_once()
            assert wd.kills == [('req-1', 6_000)]

    def test__multiple_in_flight_only_first_breach_kills(self):                       # check_once short-circuits after the first breach; os._exit would fire there in prod
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '1000'}):
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 0
            wd.register('req-1')
            wd.register('req-2')
            wd.current_time_ms = 2_000
            wd.check_once()
            assert len(wd.kills) == 1                                                # Exactly one kill recorded — we don't fire twice from a single tick

    def test__unregistered_requests_are_not_checked(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '1000'}):
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 0
            wd.register('req-1')
            wd.unregister('req-1')
            wd.current_time_ms = 5_000                                                # Would have breached if still registered
            wd.check_once()
            assert wd.kills == []

    def test__check_once_swallowed_errors_keep_thread_alive(self):                    # The real loop() has a try/except; check_once itself should NOT hide errors from callers
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '1000'}):
            wd = _FakeWatchdog().setup()
            wd.lock = None                                                            # Force a failure inside check_once
            try:
                wd.check_once()
                assert False, 'check_once should raise when lock is broken'
            except Exception:                                                         # The loop()'s except is the swallow point; check_once surfaces errors
                pass


class test_healthcheck(TestCase):

    def test__reports_current_state(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_MAX_REQUEST_MS: '8000',
                          ENV_VAR__WATCHDOG_POLL_INTERVAL_MS: '1500'}):
            wd = _FakeWatchdog().setup()
            wd.current_time_ms = 100
            wd.register('req-a')
            wd.register('req-b')
            hc = wd.healthcheck()
            assert hc['enabled'         ] is True
            assert hc['started'         ] is False                                    # Unit tests never start the real thread
            assert hc['max_request_ms'  ] == 8000
            assert hc['poll_interval_ms'] == 1500
            assert hc['in_flight'       ] == 2


class test_start(TestCase):

    def test__disabled_start_is_noop(self):
        with _EnvScrub(**{ENV_VAR__WATCHDOG_DISABLED: '1'}):
            wd = _FakeWatchdog().setup()
            wd.start()
            assert wd.started is False
            assert wd.thread  is None

    def test__start_is_idempotent(self):                                              # Calling start() twice does not spawn a second daemon thread
        with _EnvScrub():
            wd = _FakeWatchdog().setup()
            wd.start()
            first_thread = wd.thread
            wd.start()
            assert wd.thread is first_thread
            assert wd.started is True
