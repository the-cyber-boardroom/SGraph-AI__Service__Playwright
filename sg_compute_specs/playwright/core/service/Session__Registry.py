# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Session__Registry (Φ7 — opt-in stateful)
#
# In-process map: session_id → held browser + page + buffer + expiry.
# Single-instance only — no cross-replica sharing. The plan's "Out" line
# explicitly accepts this: sticky-session routing is unnecessary for the
# single ephemeral EC2 / Lambda we target.
#
# Lifecycle:
#   open   — Browser__Launcher.launch + create page + attach buffer →
#            store with expires_at_ms. Returns the session_id.
#   get    — Lookup + REFRESH TTL (every access bumps the deadline).
#            Returns None for unknown / expired.
#   close  — Browser__Launcher.stop (idempotent) + pop from map.
#   sweep  — Best-effort expired-session cleanup. Cheap O(n) scan; called
#            at the start of every operation (no background thread —
#            simpler, no race conditions, no shutdown hook needed).
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid
from typing                                                                                         import Any, Dict, List, Optional

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sg_compute_specs.playwright.core.service.Browser__Launcher                                         import Browser__Launcher
from sg_compute_specs.playwright.core.service.Page__Listeners__Buffer                                   import Page__Listeners__Buffer


def _now_ms() -> int:
    return int(time.time() * 1000)


class Session__State:                                                               # Held per-session — NOT Type_Safe because it holds opaque browser/page handles
    def __init__(self, session_id: Session_Id, browser, page, buffer: Page__Listeners__Buffer,
                 ttl_ms: int, capture_config=None, credentials=None):
        self.session_id     = session_id
        self.browser        = browser
        self.page           = page
        self.buffer         = buffer
        self.ttl_ms         = int(ttl_ms)
        self.expires_at_ms  = _now_ms() + int(ttl_ms)
        self.capture_config = capture_config                                        # Default capture config for /act + /probe calls
        self.credentials    = credentials

    def is_expired(self) -> bool:
        return _now_ms() >= self.expires_at_ms

    def refresh_ttl(self) -> None:
        self.expires_at_ms = _now_ms() + self.ttl_ms                                # Every access bumps the deadline by the original ttl_ms


class Session__Registry(Type_Safe):

    browser_launcher : Browser__Launcher = None                                     # Injected by Playwright__Service.setup() — reuses the same launcher as /sequence/execute

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sessions : Dict[str, Session__State] = {}                             # session_id (str) → state. Underscore prefix is OK on instance state; rule 9 is about METHODS.

    def open(self, browser_config: Schema__Browser__Config, ttl_ms: int,
             capture_config=None, credentials=None) -> Session__State:
        self.sweep_expired()
        session_id    = Session_Id()
        launch_result = self.browser_launcher.launch(browser_config or Schema__Browser__Config())
        self.browser_launcher.register(session_id, launch_result)
        browser       = launch_result.browser
        page          = self._get_or_create_page(browser)
        buffer        = Page__Listeners__Buffer()
        try:
            buffer.attach(page)
        except Exception:
            buffer = None
        state = Session__State(session_id    = session_id    ,
                               browser       = browser       ,
                               page          = page          ,
                               buffer        = buffer        ,
                               ttl_ms        = ttl_ms        ,
                               capture_config= capture_config,
                               credentials   = credentials   )
        self._sessions[str(session_id)] = state
        return state

    def get(self, session_id: str) -> Optional[Session__State]:                     # Lookup + refresh TTL. None if not found OR expired (closes expired ones too)
        self.sweep_expired()
        state = self._sessions.get(str(session_id))
        if state is None:
            return None
        if state.is_expired():
            self._close_state(state)
            return None
        state.refresh_ttl()
        return state

    def close(self, session_id: str) -> bool:                                       # True if a session was closed, False if not found
        state = self._sessions.pop(str(session_id), None)
        if state is None:
            return False
        self._close_state(state)
        return True

    def sweep_expired(self) -> int:                                                 # Returns the count cleaned up — useful for tests + observability
        now = _now_ms()
        expired_ids = [sid for sid, st in self._sessions.items() if now >= st.expires_at_ms]
        for sid in expired_ids:
            state = self._sessions.pop(sid, None)
            if state is not None:
                self._close_state(state)
        return len(expired_ids)

    def session_ids(self) -> List[str]:                                              # Snapshot of currently-active session ids (post-sweep)
        self.sweep_expired()
        return list(self._sessions.keys())

    # ─── Private helpers ───────────────────────────────────────────────────────

    def _close_state(self, state: Session__State) -> None:
        try:
            self.browser_launcher.stop(state.session_id)
        except Exception:
            pass                                                                    # Idempotent + best-effort — close must NEVER raise

    def _get_or_create_page(self, browser: Any) -> Any:                              # Same pattern as Sequence__Runner.get_or_create_page (kept local to avoid coupling)
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
        else:
            context = browser.new_context()
        pages = context.pages
        if pages:
            return pages[0]
        return context.new_page()
