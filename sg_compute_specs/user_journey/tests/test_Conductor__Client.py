# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Conductor__Client.parse_status (pure typed reconstruction)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.clients.Conductor__Client            import Conductor__Client
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State     import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status import Schema__Suite__Run__Status
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status   import Schema__Worker__Status


class TestParseStatus:

    def test__reconstructs_suite_snapshot(self):
        snapshot = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        snapshot.workers.append(Schema__Worker__Status(state=Enum__Worker__State.PASSED, journey_id='login'))
        snapshot.counts.passed = 1

        restored = Conductor__Client().parse_status(snapshot.json())                # the wire round-trip the client performs
        assert isinstance(restored, Schema__Suite__Run__Status)
        assert restored.state              == Enum__Suite__Run__State.RUNNING
        assert int(restored.counts.passed) == 1
        assert len(restored.workers)       == 1
        assert restored.workers[0].state   == Enum__Worker__State.PASSED

    def test__headers_include_api_key_when_set(self):
        assert Conductor__Client(api_key='secret')._headers() == {'X-API-Key': 'secret'}
        assert Conductor__Client()._headers()                 == {}
