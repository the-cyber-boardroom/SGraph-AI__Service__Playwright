# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Request__Watchdog
#
# AWS Lambda gives us no external way to kill a stuck invocation. If the main
# thread deadlocks — Playwright sync-API-inside-asyncio poisoning, a hung
# proxy CONNECT, a wedged GIL, whatever — the container stays alive consuming
# billed time until the Lambda lifetime expires (minutes to hours). Meanwhile
# callers see CloudFront 504s and nothing recovers on its own.
#
# This watchdog runs in its own daemon thread. It tracks the start time of
# every in-flight HTTP request (via an HTTP middleware wired in
# Fast_API__Playwright__Service.setup()). Every `poll_interval_ms` it takes a
# snapshot of in-flight requests, checks durations, and if any request has
# exceeded `max_request_ms` it calls os._exit(2). LWA sees the process die,
# AWS exits the Lambda execution environment, and the next invocation gets a
# fresh container.
#
# Why this specifically works when nothing else does:
#   • The watchdog is a SEPARATE OS THREAD. `time.sleep` releases the GIL.
#     Even if the main thread is fully deadlocked on a blocking syscall, the
#     watchdog thread still runs on its scheduled tick.
#   • os._exit is a C-level syscall — it bypasses Python cleanup, atexit
#     handlers, finally blocks, signal handlers, and even GIL contention.
#     The process is terminated immediately.
#   • LWA treats the death of the backend process as a container failure.
#     AWS Lambda provisions a fresh execution environment on the next invoke.
#
# Testability: `now_ms` and `kill` are method seams. Tests subclass to freeze
# the clock and record kill() invocations instead of terminating the test
# runner. The background thread itself is NOT started in unit tests —
# `check_once()` is called directly.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import threading
import time
from typing                                                                                       import Any, Dict, List, Tuple

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe
from osbot_utils.utils.Env                                                                        import get_env

from sgraph_ai_service_playwright.consts.env_vars                                                 import (ENV_VAR__WATCHDOG_DISABLED        ,
                                                                                                          ENV_VAR__WATCHDOG_MAX_REQUEST_MS   ,
                                                                                                          ENV_VAR__WATCHDOG_POLL_INTERVAL_MS )
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds              import Safe_UInt__Milliseconds


DEFAULT_MAX_REQUEST_MS   = 28000                                                    # 2 s headroom under CloudFront's 30 s gateway timeout
DEFAULT_POLL_INTERVAL_MS = 2000                                                     # Fast enough to fire before CF, slow enough to stay cheap


class Request__Watchdog(Type_Safe):
    in_flight        : Dict[str, int]                                               # request_id → epoch-ms start stamp (wall-clock, NOT a duration — Safe_UInt__Milliseconds caps at 15 min and would reject epoch values)
    max_request_ms   : Safe_UInt__Milliseconds                                      # Duration — exceed → os._exit(2). Set via ENV_VAR__WATCHDOG_MAX_REQUEST_MS or DEFAULT.
    poll_interval_ms : Safe_UInt__Milliseconds                                      # Duration — background-thread tick. Set via ENV_VAR__WATCHDOG_POLL_INTERVAL_MS or DEFAULT.
    disabled         : bool = False                                                 # ENV_VAR__WATCHDOG_DISABLED='1' → register/unregister are no-ops, thread never starts.
    lock             : Any  = None                                                  # threading.Lock — created in setup() to keep the constructor side-effect-free
    thread           : Any  = None                                                  # threading.Thread — created in start()
    started          : bool = False

    def setup(self):
        env_max  = get_env(ENV_VAR__WATCHDOG_MAX_REQUEST_MS  )
        env_poll = get_env(ENV_VAR__WATCHDOG_POLL_INTERVAL_MS)
        env_off  = get_env(ENV_VAR__WATCHDOG_DISABLED        )

        max_ms  = int(env_max ) if env_max  else DEFAULT_MAX_REQUEST_MS
        poll_ms = int(env_poll) if env_poll else DEFAULT_POLL_INTERVAL_MS

        self.max_request_ms   = Safe_UInt__Milliseconds(max_ms )
        self.poll_interval_ms = Safe_UInt__Milliseconds(poll_ms)
        self.disabled         = (env_off == '1')
        self.lock             = threading.Lock()
        return self

    def start(self):
        if self.disabled or self.started:
            return self                                                              # No-op in disabled / test envs
        self.thread = threading.Thread(target=self.loop, daemon=True, name='Request__Watchdog')
        self.thread.start()
        self.started = True
        return self

    def register(self, request_id: str) -> None:
        if self.disabled:
            return
        with self.lock:
            self.in_flight[request_id] = self.now_ms()                               # Plain int — epoch millis overflow Safe_UInt__Milliseconds' 15-min cap

    def unregister(self, request_id: str) -> None:
        if self.disabled:
            return
        with self.lock:
            self.in_flight.pop(request_id, None)

    def loop(self):                                                                  # Background thread body — wakes every poll_interval_ms, never dies
        while True:
            time.sleep(int(self.poll_interval_ms) / 1000.0)
            try:
                self.check_once()
            except Exception:                                                        # A noisy watchdog is better than a dead one
                pass

    def check_once(self) -> None:
        now         = self.now_ms()
        max_ms      = int(self.max_request_ms)
        breaches    : List[Tuple[str, int]] = []                                     # (request_id, duration_ms) — collected under the lock, acted on after release

        with self.lock:
            snapshot = dict(self.in_flight)                                          # Snapshot to avoid holding the lock while calling kill / os._exit

        for request_id, started_ms in snapshot.items():
            duration = now - started_ms
            if duration > max_ms:
                breaches.append((request_id, duration))

        for request_id, duration in breaches:
            self.kill(request_id, duration)
            return                                                                   # Unreachable once os._exit fires; test doubles return

    def kill(self, request_id: str, duration_ms: int) -> None:
        msg = (f'[Request__Watchdog] request_id={request_id} exceeded '
               f'max_request_ms={int(self.max_request_ms)} (duration={duration_ms} ms) — '
               f'forcing Lambda recycle via os._exit(2)\n')
        sys.stderr.write(msg)                                                        # Flushes eagerly because stderr is usually unbuffered, but call flush to be sure
        sys.stderr.flush()
        os._exit(2)                                                                  # C-level exit — bypasses Python cleanup, works even when main thread is wedged

    def healthcheck(self) -> Dict[str, Any]:                                          # Surfaced from /health/status for visibility
        return { 'enabled'          : not self.disabled                        ,
                 'started'          : self.started                             ,
                 'max_request_ms'   : int(self.max_request_ms  )               ,
                 'poll_interval_ms' : int(self.poll_interval_ms)               ,
                 'in_flight'        : len(self.in_flight       )               }

    def now_ms(self) -> int:                                                          # Seam — tests subclass to freeze time
        return int(time.time() * 1000)
