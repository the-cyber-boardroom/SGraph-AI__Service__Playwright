# ═══════════════════════════════════════════════════════════════════════════════
# Tests — User_Journey__Cockpit__Render (pure cockpit content)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State      import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status     import Schema__Worker__Status
from sg_compute_specs.user_journey.tui.render.User_Journey__Cockpit__Render       import User_Journey__Cockpit__Render


def _status():
    status          = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
    status.suite_id = 'checkout-load'
    for state in (Enum__Worker__State.PASSED, Enum__Worker__State.PASSED,
                  Enum__Worker__State.FAILED, Enum__Worker__State.RUNNING):
        status.workers.append(Schema__Worker__Status(state=state))
    status.counts.passed  = 2
    status.counts.failed  = 1
    status.counts.running = 1
    status.aggregates.latency_p50_ms = 190
    status.aggregates.latency_p95_ms = 420
    status.aggregates.flows_total    = 1280
    return status


class TestCockpitRender:

    def test__worker_glyphs(self):
        render = User_Journey__Cockpit__Render()
        assert render.worker_glyph(Enum__Worker__State.PASSED)  == '✓'
        assert render.worker_glyph(Enum__Worker__State.FAILED)  == '✗'
        assert render.worker_glyph(Enum__Worker__State.RUNNING) == '⠿'

    def test__worker_grid(self):
        grid = User_Journey__Cockpit__Render().worker_grid(_status())
        assert grid == '✓ ✓ ✗ ⠿'

    def test__header_line(self):
        header = User_Journey__Cockpit__Render().header_line(_status())
        assert 'checkout-load' in header
        assert '2/4 ✓'        in header                                            # passed/total

    def test__aggregates_line(self):
        line = User_Journey__Cockpit__Render().aggregates_line(_status())
        assert 'passed 2'   in line
        assert 'failed 1'   in line
        assert 'p50 190ms'  in line
        assert 'p95 420ms'  in line
        assert 'flows 1280' in line

    def test__lines_has_three_rows(self):
        lines = User_Journey__Cockpit__Render().lines(_status())
        assert len(lines)   == 3
        assert lines[2]     == '✓ ✓ ✗ ⠿'

    def test__empty_suite_renders_dash_and_zero(self):
        empty  = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.PENDING)
        render = User_Journey__Cockpit__Render()
        assert '—'   in render.header_line(empty)
        assert '0/0' in render.header_line(empty)
        assert render.worker_grid(empty) == ''
