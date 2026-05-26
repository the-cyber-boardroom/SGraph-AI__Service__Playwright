# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/screens/user_journey tests: cockpit body_markup (no running terminal)
# Textual is a 3.12 dep; importorskip keeps this clean if it's ever absent.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

pytest.importorskip('textual')

from sgraph_ai_service_playwright__cli.tui.screens.user_journey.User_Journey__Cockpit__Screen import User_Journey__Cockpit__Screen

from sg_compute_specs.user_journey.core.clients.Conductor__Client                import Conductor__Client
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State    import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State         import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status  import Schema__Suite__Run__Status
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status      import Schema__Worker__Status


class _Canned_Conductor(Conductor__Client):
    def get_suite(self, suite_run_id):
        if suite_run_id == 'missing':
            return None
        status          = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        status.suite_id = 'checkout-load'
        status.workers.append(Schema__Worker__Status(state=Enum__Worker__State.PASSED))
        status.workers.append(Schema__Worker__Status(state=Enum__Worker__State.RUNNING))
        status.counts.passed  = 1
        status.counts.running = 1
        return status


def test_body_markup_renders_snapshot():
    screen = User_Journey__Cockpit__Screen(conductor=_Canned_Conductor(), suite_run_id='r1')
    markup = screen.body_markup()
    assert 'checkout-load' in markup
    assert '✓ ⠿'           in markup                                               # the worker grid
    assert 'passed 1'      in markup


def test_body_markup_no_suite_selected():
    assert User_Journey__Cockpit__Screen().body_markup() == 'no suite selected'


def test_body_markup_unknown_run():
    screen = User_Journey__Cockpit__Screen(conductor=_Canned_Conductor(), suite_run_id='missing')
    assert screen.body_markup() == 'no suite run missing'
