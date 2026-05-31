# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Page__Listeners__Buffer (Φ4 — load-time forensics)
#
# Per-page event buffer. Sequence__Runner attaches this BEFORE the first
# navigate so load-time console messages + network requests are captured
# (the events fire during goto, not after).
#
# Buffered events:
#   • console_events  — page.on('console')        : {type, text, location}
#   • request_events  — page.on('request')        : {url, method, resource_type}
#   • response_events — page.on('response')       : {url, status, ok}
#   • failed_events   — page.on('requestfailed')  : {url, method, failure_text}
#
# Live state:
#   • in_flight_ids   — set of request id()s currently outstanding (cleared
#                       by 'response' OR 'requestfailed'). The
#                       `wait_for: network_idle_ms` predicate watches this.
#
# Bounded: each buffer caps at MAX_EVENTS_PER_KIND to keep memory predictable
# on long-running pages; oldest events evict first (ring-buffer semantics
# via list slicing).
#
# The buffer is attached to the page as `page._sgpw_buffer` — monkey-patch
# pattern keeps the Step__Executor signature stable while letting verbs
# reach buffered state.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                                         import Any, Dict, List, Set

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe


MAX_EVENTS_PER_KIND = 1000                                                          # Per-kind ring-buffer cap; keeps memory predictable on long pages
PAGE_ATTR_NAME      = '_sgpw_buffer'                                                # Convention for attaching buffer to a Playwright page


class Page__Listeners__Buffer(Type_Safe):

    console_events  : List[Dict]                                                    # page.on('console') sink
    request_events  : List[Dict]                                                    # page.on('request') sink
    response_events : List[Dict]                                                    # page.on('response') sink
    failed_events   : List[Dict]                                                    # page.on('requestfailed') sink
    in_flight_ids   : Set[int]                                                      # Currently-outstanding request id()s — len gives concurrency
    attached_to_id  : int = 0                                                       # id() of page we're attached to; 0 = unattached

    def attach(self, page: Any) -> None:                                            # Wire listeners + park self on the page
        page.on('console'      , self._on_console      )
        page.on('request'      , self._on_request      )
        page.on('response'     , self._on_response     )
        page.on('requestfailed', self._on_request_failed)
        setattr(page, PAGE_ATTR_NAME, self)
        self.attached_to_id = id(page)

    # ─── Event handlers — defensive; one bad message must not break the page ───

    def _on_console(self, msg: Any) -> None:
        try:
            event = {'type'      : safe_str_attr(msg, 'type'),                      # 'log' | 'warn' | 'error' | 'info' | …
                     'text'      : safe_str_attr(msg, 'text'),
                     'timestamp' : _now_ms()                  }
            location = getattr(msg, 'location', None)
            if location is not None:
                event['location'] = {'url'         : safe_str_attr(location, 'url'        , default='') ,
                                     'lineNumber'  : safe_int_attr(location, 'lineNumber' , default=0)  ,
                                     'columnNumber': safe_int_attr(location, 'columnNumber', default=0) }
            self.console_events.append(event)
            self._trim(self.console_events)
        except Exception:
            pass                                                                    # Buffer must never crash the page

    def _on_request(self, request: Any) -> None:
        try:
            self.in_flight_ids.add(id(request))
            self.request_events.append({'url'           : safe_str_attr(request, 'url'),
                                        'method'        : safe_str_attr(request, 'method'),
                                        'resource_type' : safe_str_attr(request, 'resource_type'),
                                        'timestamp'     : _now_ms()                              })
            self._trim(self.request_events)
        except Exception:
            pass

    def _on_response(self, response: Any) -> None:
        try:
            req = getattr(response, 'request', None)
            if req is not None:
                self.in_flight_ids.discard(id(req))
            status = safe_int_attr(response, 'status', default=0)
            self.response_events.append({'url'       : safe_str_attr(response, 'url'),
                                         'status'    : status                       ,
                                         'ok'        : 200 <= status < 400          ,
                                         'timestamp' : _now_ms()                    })
            self._trim(self.response_events)
        except Exception:
            pass

    def _on_request_failed(self, request: Any) -> None:
        try:
            self.in_flight_ids.discard(id(request))
            self.failed_events.append({'url'          : safe_str_attr(request, 'url'),
                                       'method'       : safe_str_attr(request, 'method'),
                                       'failure_text' : safe_str_attr(request, 'failure', default='') or
                                                        safe_str_attr(getattr(request, 'failure', None), 'errorText', default=''),
                                       'timestamp'    : _now_ms()                                                            })
            self._trim(self.failed_events)
        except Exception:
            pass

    def _trim(self, events: List[Dict]) -> None:                                    # In-place trim; protects against unbounded growth on long-running pages
        if len(events) > MAX_EVENTS_PER_KIND:
            del events[:len(events) - MAX_EVENTS_PER_KIND]

    # ─── Read helpers — used by verbs + end-of-sequence artefact emission ──────

    def in_flight_count(self) -> int:
        return len(self.in_flight_ids)

    def console_tail(self, lines: int) -> List[Dict]:
        return list(self.console_events[-int(lines):]) if lines > 0 else []

    def network_failures(self) -> List[Dict]:
        return list(self.failed_events)

    def network_snapshot(self) -> Dict:                                              # End-of-sequence aggregate for artefact emission
        return {'requests'  : list(self.request_events) ,
                'responses' : list(self.response_events),
                'failed'    : list(self.failed_events)  }


# ─── Helpers (module-level so they're picklable + easy to test) ────────────────

def _now_ms() -> int:
    return int(time.time() * 1000)


def safe_str_attr(obj: Any, name: str, default: str = '') -> str:
    if obj is None:
        return default
    try:
        value = getattr(obj, name, default)
        if callable(value):                                                          # Playwright wraps some fields as no-arg methods
            value = value()
        return str(value) if value is not None else default
    except Exception:
        return default


def safe_int_attr(obj: Any, name: str, default: int = 0) -> int:
    if obj is None:
        return default
    try:
        value = getattr(obj, name, default)
        if callable(value):
            value = value()
        return int(value) if value is not None else default
    except Exception:
        return default


def buffer_from_page(page: Any) -> 'Page__Listeners__Buffer':                       # None when the runner hasn't attached one (unit tests bypassing the runner); callers must tolerate
    return getattr(page, PAGE_ATTR_NAME, None)
