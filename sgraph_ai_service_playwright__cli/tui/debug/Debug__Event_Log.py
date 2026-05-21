# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui debug: Debug__Event_Log
# The reusable under-the-hood feed. A service is handed one of these and calls
# record(category, message, detail) around the work it does (S3 list/get, fs write,
# AWS API call); the Debug Panel renders it. This is the seam that makes "what is
# going on under the hood" visible across every TUI in the sg aws ecosystem — inject
# the same log into a source and a screen and the panel lights up. Bounded ring
# (max_events) so a long sync can't grow it without limit. Plain class — not textual.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                          import Type_Safe

from sgraph_ai_service_playwright__cli.tui.debug.List__Debug_Event   import List__Debug_Event
from sgraph_ai_service_playwright__cli.tui.debug.Schema__Debug_Event import Schema__Debug_Event


class Debug__Event_Log(Type_Safe):
    max_events : int = 1000
    next_seq   : int = 0
    events     : List__Debug_Event

    def record(self, category : str, message : str, detail : str = '', ok : bool = True) -> Schema__Debug_Event:
        event = Schema__Debug_Event(seq=self.next_seq, ts=time.time(), category=category, message=message, detail=detail, ok=ok)
        self.next_seq += 1
        self.events.append(event)
        if len(self.events) > self.max_events:                                       # trim oldest — bounded ring
            del self.events[:len(self.events) - self.max_events]
        return event

    def error(self, category : str, message : str, detail : str = '') -> Schema__Debug_Event:
        return self.record(category, message, detail, ok=False)

    def tail(self, n : int = 0) -> list:
        items = list(self.events)
        return items[-n:] if n else items

    def count(self) -> int:
        return len(self.events)

    def clear(self) -> None:
        self.events.clear()
