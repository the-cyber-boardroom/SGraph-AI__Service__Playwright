# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Session__Worker (Φ7-proper)
#
# One dedicated background thread per held session. The thread OWNS the
# Playwright runtime + browser + page for that session's whole lifetime,
# from `open` to `close` (or TTL expiry). Every act/probe call against the
# session marshals its work onto this thread via a queue and blocks on the
# result.
#
# Why this exists:
#   Playwright's sync API is greenlet-based. The Playwright Node subprocess
#   + dispatcher is started on the thread that first calls sync_playwright().
#   Calling page.goto / page.locator(...) from a DIFFERENT thread leads to
#   undefined behaviour (deadlocks, silent hangs, or "navigate failed" with
#   no error_message — the exact symptom session_act was hitting in CI).
#
#   The original Φ7 design wrapped each session_act/probe call in a fresh
#   ThreadPoolExecutor — convenient for escaping the asyncio loop, but
#   broken for held state because each request landed on a NEW thread.
#
#   This worker keeps the Playwright runtime + page on ONE thread for the
#   session's lifetime. The asyncio-loop escape problem is also solved:
#   the worker thread is freshly spawned with no event loop, so Playwright
#   sync is happy there.
#
# Idle cost: the worker blocks on queue.get() — 0% CPU, ~few KB of RAM
# (one Python thread + a small queue). N workers for N active sessions.
# ═══════════════════════════════════════════════════════════════════════════════

import queue
import threading
from concurrent.futures                                                                             import Future
from typing                                                                                         import Any, Callable, Dict, Optional


_POISON_PILL = object()                                                             # Sentinel pushed to inbox by stop() — signals the worker thread to teardown + exit


class Session__Worker:                                                              # NOT Type_Safe — owns threading primitives + opaque Playwright handles

    SETUP_TIMEOUT_S    = 60.0                                                       # Max time to wait for browser launch + page creation on worker thread
    TEARDOWN_TIMEOUT_S = 10.0                                                       # Max time to wait for the worker to drain + exit during stop()

    def __init__(self):
        self._inbox        : queue.Queue = queue.Queue()
        self._thread       : Optional[threading.Thread] = None
        self._state        : Dict[str, Any] = {}                                    # Caller-supplied state populated by launch_fn on the worker thread (e.g. browser/page/buffer/launch_result)
        self._setup_done   : threading.Event = threading.Event()
        self._setup_error  : Optional[BaseException] = None
        self._stopped      : threading.Event = threading.Event()
        self._teardown_fn  : Optional[Callable] = None                              # Stored from start(), called on the worker thread during shutdown

    # ── Lifecycle (called from the asyncio / FastAPI handler thread) ──────────

    def start(self, launch_fn: Callable[[], Dict[str, Any]],                        # launch_fn runs on the worker thread; returns the state dict (browser/page/buffer)
              teardown_fn: Callable[[Dict[str, Any]], None] = None                  # teardown_fn runs on the worker thread during stop(); receives the same state dict
         ) -> Dict[str, Any]:
        self._teardown_fn = teardown_fn
        self._thread = threading.Thread(target=self._run, args=(launch_fn,), daemon=True, name='SgPlaywright-Session')
        self._thread.start()
        if not self._setup_done.wait(timeout=self.SETUP_TIMEOUT_S):
            raise TimeoutError(f'Session worker setup did not complete within {self.SETUP_TIMEOUT_S}s')
        if self._setup_error is not None:
            raise self._setup_error
        return dict(self._state)                                                    # shallow copy — caller can store references but mutations don't leak

    def submit(self, fn: Callable, *args, **kwargs) -> Any:                         # Marshals fn(*args, **kwargs) onto the worker thread; blocks the caller until the worker returns
        if self._stopped.is_set():
            raise RuntimeError('Session__Worker has been stopped')
        fut : Future = Future()
        self._inbox.put((fn, args, kwargs, fut))
        return fut.result()                                                         # Raises whatever fn raised — full traceback preserved

    def stop(self) -> None:                                                         # Idempotent — multiple calls + post-stop submits are no-ops
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._inbox.put(_POISON_PILL)
        if self._thread is not None:
            self._thread.join(timeout=self.TEARDOWN_TIMEOUT_S)                      # Best-effort — daemon thread dies with the process anyway

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Worker thread loop (runs on the dedicated thread) ─────────────────────

    def _run(self, launch_fn: Callable[[], Dict[str, Any]]) -> None:
        try:
            self._state = launch_fn() or {}                                         # Browser launch + page creation happens HERE — on the worker thread, with no asyncio loop, with greenlet-friendly thread context
        except BaseException as setup_error:
            self._setup_error = setup_error
            self._setup_done.set()
            return
        self._setup_done.set()

        try:
            while True:
                task = self._inbox.get()
                if task is _POISON_PILL:
                    break
                fn, args, kwargs, fut = task
                try:
                    result = fn(*args, **kwargs)
                    fut.set_result(result)
                except BaseException as e:
                    fut.set_exception(e)
        finally:
            if self._teardown_fn is not None:
                try:
                    self._teardown_fn(self._state)                                  # Run teardown on the worker thread (browser.close etc. must happen here for the same Playwright-affinity reason)
                except Exception:
                    pass                                                            # Never raise during teardown
