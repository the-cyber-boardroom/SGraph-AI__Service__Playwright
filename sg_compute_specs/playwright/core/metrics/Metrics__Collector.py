# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Metrics__Collector
#
# Module-level Prometheus Counter and Histogram objects bound to a dedicated
# CollectorRegistry (_REGISTRY). Using a private registry instead of the
# default REGISTRY avoids test pollution and allows clean serialisation via
# generate_latest(_REGISTRY).
#
# record_timings() is called by Playwright__Service after each completed
# request (success or error). Routes__Metrics calls generate_metrics() to
# serialise the registry for GET /metrics.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
from typing                                                                          import Optional

from prometheus_client                                                               import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe

from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings        import Schema__Sequence__Timings

_REGISTRY = CollectorRegistry()

_REQUEST_TOTAL = Counter(
    'sg_playwright_request_total',
    'Total completed requests by endpoint and HTTP-class status',
    ['endpoint', 'status'],
    registry = _REGISTRY,
)

_REQUEST_DURATION_SECONDS = Histogram(
    'sg_playwright_request_duration_seconds',
    'End-to-end request wall-clock duration in seconds',
    ['endpoint'],
    buckets  = [1, 2, 5, 10, 20, 30, 45, 60, 90, 120],
    registry = _REGISTRY,
)

_CHROMIUM_LAUNCH_SECONDS = Histogram(
    'sg_playwright_chromium_launch_seconds',
    'Chromium launch duration in seconds (browser_launch_ms)',
    buckets  = [.5, 1, 2, 3, 5, 8, 13, 21, 30],
    registry = _REGISTRY,
)

_NAVIGATE_SECONDS = Histogram(
    'sg_playwright_navigate_seconds',
    'Navigation step wall-clock duration in seconds (steps_ms)',
    buckets  = [.5, 1, 2, 3, 5, 8, 13, 21, 30],
    registry = _REGISTRY,
)

_CHROMIUM_TEARDOWN_SECONDS = Histogram(
    'sg_playwright_chromium_teardown_seconds',
    'browser.close() + playwright.stop() duration in seconds (browser_close_ms)',
    buckets  = [.05, .1, .25, .5, 1, 2],
    registry = _REGISTRY,
)

_TOTAL_DURATION_SECONDS = Histogram(
    'sg_playwright_total_duration_seconds',
    'Outer wall-clock duration in seconds including all phases (total_ms)',
    buckets  = [1, 2, 5, 10, 20, 30, 45, 60, 90, 120],
    registry = _REGISTRY,
)


class Metrics__Collector(Type_Safe):

    def record_timings(self, timings: Optional[Schema__Sequence__Timings],         # timings=None on error paths
                       endpoint: str, status: str) -> None:
        _REQUEST_TOTAL.labels(endpoint=endpoint, status=status).inc()
        if timings is None:
            return
        total_ms  = int(timings.total_ms)
        launch_ms = int(timings.browser_launch_ms)
        steps_ms  = int(timings.steps_ms)
        close_ms  = int(timings.browser_close_ms)
        if total_ms  > 0: _REQUEST_DURATION_SECONDS.labels(endpoint=endpoint).observe(total_ms  / 1000)
        if total_ms  > 0: _TOTAL_DURATION_SECONDS                            .observe(total_ms  / 1000)
        if launch_ms > 0: _CHROMIUM_LAUNCH_SECONDS                           .observe(launch_ms / 1000)
        if steps_ms  > 0: _NAVIGATE_SECONDS                                  .observe(steps_ms  / 1000)
        if close_ms  > 0: _CHROMIUM_TEARDOWN_SECONDS                         .observe(close_ms  / 1000)

    def generate_metrics(self) -> bytes:
        return generate_latest(_REGISTRY)

    def content_type(self) -> str:
        return CONTENT_TYPE_LATEST
