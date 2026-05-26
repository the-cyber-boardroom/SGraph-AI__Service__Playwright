# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Suite__Runner (fan-out planning)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.conductor.Suite__Runner                  import Suite__Runner
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Definition  import Schema__Suite__Definition
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Entry       import Schema__Suite__Entry


class TestExpandEntry:

    def test__one_spec_per_replica(self):
        entry = Schema__Suite__Entry(journey_id='checkout', count=3, concurrency=2)
        specs = Suite__Runner().expand_entry(entry, default_image='diniscruz/sg-journey-runner:latest')
        assert len(specs)                  == 3
        assert str(specs[0].worker_id)     == 'checkout-00000'
        assert str(specs[2].worker_id)     == 'checkout-00002'
        assert str(specs[0].run_id)        == 'checkout-00000'                      # run_id == worker_id (X-SG-Run-Id)
        assert str(specs[0].journey_id)    == 'checkout'
        assert str(specs[0].worker_image)  == 'diniscruz/sg-journey-runner:latest'  # default applied

    def test__entry_image_overrides_default(self):
        entry = Schema__Suite__Entry(worker_image='diniscruz/sg-vault-journey:latest', journey_id='vault', count=1)
        specs = Suite__Runner().expand_entry(entry, default_image='diniscruz/sg-journey-runner:latest')
        assert str(specs[0].worker_image) == 'diniscruz/sg-vault-journey:latest'


class TestChunking:

    def test__even_split(self):
        runner = Suite__Runner()
        waves  = runner.chunk(list(range(500)), 50)
        assert len(waves)        == 10
        assert all(len(w) == 50 for w in waves)

    def test__uneven_split_last_wave_smaller(self):
        runner = Suite__Runner()
        waves  = runner.chunk(list(range(7)), 3)
        assert [len(w) for w in waves] == [3, 3, 1]

    def test__zero_concurrency_falls_back_to_one(self):
        runner = Suite__Runner()
        waves  = runner.chunk([1, 2], 0)
        assert [len(w) for w in waves] == [1, 1]


class TestPlan:

    def test__plan_concatenates_per_entry_waves(self):
        suite = Schema__Suite__Definition(suite_id='nightly')
        suite.entries.append(Schema__Suite__Entry(journey_id='login',  count=1,  concurrency=1))   # 1 wave
        suite.entries.append(Schema__Suite__Entry(journey_id='browse', count=20, concurrency=5))   # 4 waves
        waves = Suite__Runner().plan(suite, default_image='diniscruz/sg-journey-runner:latest')
        assert len(waves)               == 5                                        # 1 + 4
        assert len(waves[0])            == 1
        assert all(len(w) == 5 for w in waves[1:])
        assert str(waves[0][0].journey_id) == 'login'
        assert str(waves[1][0].journey_id) == 'browse'
