# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Engine
#
# Which Playwright API surface executed the request: sync_playwright (SYNC) vs
# async_playwright (ASYNC). Reported on Schema__Sequence__Response so callers
# can label runs and compare reliability/latency between the two engines.
#
# Both engines are first-class, kept side-by-side by design. The Workbench
# client may pin requested_engine per call; the response always carries the
# engine that actually ran (in case a fallback ever swaps under the caller).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Engine(str, Enum):
    SYNC  = 'sync'
    ASYNC = 'async'
