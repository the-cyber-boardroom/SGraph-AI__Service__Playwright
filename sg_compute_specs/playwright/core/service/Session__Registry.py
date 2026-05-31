# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Session__Registry (Φ7-proper)
#
# In-process map: session_id → Session__State (which owns a Session__Worker
# thread that owns the Playwright runtime + browser + page).
#
# Lifecycle:
#   open   — Spawn a Session__Worker; the worker thread launches the browser
#            + creates the page + attaches the listener buffer. Store with
#            expires_at_ms.
#   get    — Lookup + refresh TTL. None for unknown / expired.
#   close  — Worker.stop() → poison pill → worker runs teardown
#            (browser.close on the SAME thread that opened it). Pop from map.
#   sweep  — Lazy expired-session cleanup. Called at the start of every
#            registry operation AND from Playwright__Service.setup() (so
#            every request to ANY endpoint sweeps idle sessions, even ones
#            that never touch /session/*). No background thread.
#
# Per-session thread cost: ~1 Python thread blocked on queue.get (0% CPU)
# + ~few KB of RAM, plus the held Chromium process. Goes away on close.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                                         import Any, Dict, List, Optional

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sg_compute_specs.playwright.core.service.Page__Listeners__Buffer                                   import Page__Listeners__Buffer
from sg_compute_specs.playwright.core.service.Session__Worker                                           import Session__Worker


def _now_ms() -> int:
    return int(time.time() * 1000)


class Session__State:                                                               # Held per-session — NOT Type_Safe (owns thread + opaque Playwright handles)
    def __init__(self, session_id: Session_Id, worker: Session__Worker,
                 browser, page, buffer: Page__Listeners__Buffer,
                 ttl_ms: int, capture_config=None, credentials=None):
        self.session_id     = session_id
        self.worker         = worker                                                # Dedicated thread owning the Playwright runtime for this session
        self.browser        = browser
        self.page           = page
        self.buffer         = buffer
        self.ttl_ms         = int(ttl_ms)
        self.expires_at_ms  = _now_ms() + int(ttl_ms)
        self.capture_config = capture_config
        self.credentials    = credentials

    def is_expired(self) -> bool:
        return _now_ms() >= self.expires_at_ms

    def refresh_ttl(self) -> None:
        self.expires_at_ms = _now_ms() + self.ttl_ms                                # Every access bumps the deadline by the original ttl_ms


class Session__Registry(Type_Safe):

    browser_launcher : Any = None                                                   # Injected by Playwright__Service.setup() — duck-typed (.launch/.register/.stop)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sessions : Dict[str, Session__State] = {}                             # session_id (str) → state

    def open(self, browser_config: Schema__Browser__Config, ttl_ms: int,
             capture_config=None, credentials=None) -> Session__State:
        self.sweep_expired()
        session_id = Session_Id()
        worker     = Session__Worker()

        # launch_fn runs ON the worker thread — every Playwright call inside
        # here is bound to the worker thread (where the runtime is owned).
        def _launch() -> Dict[str, Any]:
            launch_result = self.browser_launcher.launch(browser_config or Schema__Browser__Config())
            self.browser_launcher.register(session_id, launch_result)
            browser = launch_result.browser
            page    = self._get_or_create_page(browser)
            buffer  = Page__Listeners__Buffer()
            try:
                buffer.attach(page)
            except Exception:
                buffer = None
            return {'launch_result': launch_result, 'browser': browser, 'page': page, 'buffer': buffer}

        # teardown_fn ALSO runs on the worker thread — browser.close() MUST
        # happen on the same thread that started the runtime (Playwright
        # affinity constraint, same root cause as the launch side).
        def _teardown(state: Dict[str, Any]) -> None:
            try:
                self.browser_launcher.stop(session_id)
            except Exception:
                pass

        try:
            state_dict = worker.start(_launch, teardown_fn=_teardown)
        except BaseException:
            worker.stop()                                                            # Cleanup the half-spawned worker; don't leak the thread
            raise

        state = Session__State(session_id    = session_id              ,
                               worker        = worker                  ,
                               browser       = state_dict['browser']   ,
                               page          = state_dict['page']      ,
                               buffer        = state_dict['buffer']    ,
                               ttl_ms        = ttl_ms                  ,
                               capture_config= capture_config          ,
                               credentials   = credentials             )
        self._sessions[str(session_id)] = state
        return state

    def get(self, session_id: str) -> Optional[Session__State]:                     # Lookup + refresh TTL. None if not found OR expired (closes expired ones)
        self.sweep_expired()
        state = self._sessions.get(str(session_id))
        if state is None:
            return None
        if state.is_expired():
            self._close_state(state)
            self._sessions.pop(str(session_id), None)
            return None
        state.refresh_ttl()
        return state

    def close(self, session_id: str) -> bool:                                       # True if a session was closed, False if not found
        state = self._sessions.pop(str(session_id), None)
        if state is None:
            return False
        self._close_state(state)
        return True

    def sweep_expired(self) -> int:                                                 # Lazy cleanup; called every registry operation AND from Playwright__Service.setup()
        now = _now_ms()
        expired_ids = [sid for sid, st in self._sessions.items() if now >= st.expires_at_ms]
        for sid in expired_ids:
            state = self._sessions.pop(sid, None)
            if state is not None:
                self._close_state(state)
        return len(expired_ids)

    def session_ids(self) -> List[str]:                                              # Snapshot post-sweep — useful for /metrics and for tests
        self.sweep_expired()
        return list(self._sessions.keys())

    # ─── Private helpers ───────────────────────────────────────────────────────

    def _close_state(self, state: Session__State) -> None:                          # Triggers the worker's teardown_fn (browser.close on worker thread) + joins
        try:
            state.worker.stop()
        except Exception:
            pass                                                                    # Never raise — close must be best-effort

    def _get_or_create_page(self, browser: Any) -> Any:                              # Runs on the worker thread (called from launch_fn)
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
        else:
            context = browser.new_context()
        pages = context.pages
        if pages:
            return pages[0]
        return context.new_page()
