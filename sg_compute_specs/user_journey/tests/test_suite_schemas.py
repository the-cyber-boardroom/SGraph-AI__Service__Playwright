# ═══════════════════════════════════════════════════════════════════════════════
# Tests — User-Journey suite schemas
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State        import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State            import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.primitives.docker.Safe_Str__Docker__Image import Safe_Str__Docker__Image
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition       import Schema__Suite__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Entry            import Schema__Suite__Entry
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Run__Status      import Schema__Suite__Run__Status
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status          import Schema__Worker__Status


class TestDockerImagePrimitive:

    def test_preserves_full_image_ref(self):
        ref = Safe_Str__Docker__Image('diniscruz/sg-journey-runner:latest')
        assert str(ref) == 'diniscruz/sg-journey-runner:latest'                     # '/' and ':' preserved

    def test_rejects_spaces(self):
        with pytest.raises(ValueError):
            Safe_Str__Docker__Image('not a valid image')


class TestSuiteEntry:

    def test_defaults(self):
        entry = Schema__Suite__Entry()
        assert int(entry.count)       == 1
        assert int(entry.concurrency) == 1
        assert entry.worker_image     is None

    def test_load_knob(self):
        entry = Schema__Suite__Entry(worker_image='diniscruz/sg-journey-runner:latest',
                                     journey_id='checkout', count=500, concurrency=50)
        assert str(entry.worker_image) == 'diniscruz/sg-journey-runner:latest'
        assert int(entry.count)        == 500
        assert int(entry.concurrency)  == 50


class TestSuiteDefinition:

    def test_round_trip_with_entries(self):
        suite = Schema__Suite__Definition(suite_id='nightly-regression')
        suite.entries.append(Schema__Suite__Entry(journey_id='login',  count=1,  concurrency=1))
        suite.entries.append(Schema__Suite__Entry(journey_id='browse', count=20, concurrency=5))
        restored = Schema__Suite__Definition.from_json(suite.json())
        assert str(restored.suite_id)        == 'nightly-regression'
        assert len(restored.entries)         == 2
        assert int(restored.entries[1].count) == 20


class TestSuiteRunStatus:

    def test_auto_inits_counts_and_aggregates(self):
        status = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        assert int(status.counts.passed)         == 0
        assert int(status.aggregates.latency_p95_ms) == 0
        assert status.workers                    == []

    def test_round_trip_with_workers(self):
        status = Schema__Suite__Run__Status(state=Enum__Suite__Run__State.RUNNING)
        status.workers.append(Schema__Worker__Status(state=Enum__Worker__State.PASSED, journey_id='login'))
        status.counts.passed = 1
        restored = Schema__Suite__Run__Status.from_json(status.json())
        assert restored.state                == Enum__Suite__Run__State.RUNNING
        assert len(restored.workers)         == 1
        assert restored.workers[0].state     == Enum__Worker__State.PASSED
        assert int(restored.counts.passed)   == 1
