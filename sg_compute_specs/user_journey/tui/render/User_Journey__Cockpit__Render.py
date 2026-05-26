# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — User_Journey__Cockpit__Render (pure cockpit content)
#
# Turns a Schema__Suite__Run__Status into plain-text cockpit content: a worker grid
# (one glyph per worker), a header line, and an aggregates line. Pure — no Textual,
# no I/O — so it is fully unit-testable and reused by the Textual screen as the body
# of each refresh.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State import Enum__Worker__State

WORKER_GLYPHS = {Enum__Worker__State.PASSED : '✓', Enum__Worker__State.FAILED : '✗',
                 Enum__Worker__State.RUNNING: '⠿', Enum__Worker__State.PENDING: '·',
                 Enum__Worker__State.ERROR  : '!', Enum__Worker__State.STOPPED: '■'}


class User_Journey__Cockpit__Render(Type_Safe):

    def worker_glyph(self, state) -> str:
        return WORKER_GLYPHS.get(state, '?')

    def worker_cells(self, status) -> list:
        return [self.worker_glyph(worker.state) for worker in status.workers]

    def worker_grid(self, status) -> str:
        return ' '.join(self.worker_cells(status))

    def total(self, status) -> int:
        counts = status.counts
        return sum(int(value) for value in (counts.pending, counts.running, counts.passed, counts.failed, counts.error))

    def header_line(self, status) -> str:
        suite = str(status.suite_id) if status.suite_id is not None else '—'
        return f'suite {suite}  ·  {status.state}  ·  {int(status.counts.passed)}/{self.total(status)} ✓'

    def aggregates_line(self, status) -> str:
        counts     = status.counts
        aggregates = status.aggregates
        return (f'passed {int(counts.passed)}  failed {int(counts.failed)}  error {int(counts.error)}  ·  '
                f'p50 {int(aggregates.latency_p50_ms)}ms  p95 {int(aggregates.latency_p95_ms)}ms  '
                f'p99 {int(aggregates.latency_p99_ms)}ms  ·  '
                f'flows {int(aggregates.flows_total)} (blocked {int(aggregates.flows_blocked)})')

    def lines(self, status) -> list:
        return [self.header_line(status), self.aggregates_line(status), self.worker_grid(status)]
