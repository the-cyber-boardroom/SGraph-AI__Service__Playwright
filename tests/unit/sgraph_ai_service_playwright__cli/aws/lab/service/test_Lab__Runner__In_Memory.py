# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Runner (in-memory)
# No-op experiment end-to-end; ledger lifecycle; create_and_register ordering.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Mutation__Tier      import Enum__AWS__Mutation__Tier
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State            import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Experiment__Status      import Enum__Lab__Experiment__Status
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type           import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Int__Duration_Ms         import Safe_Int__Duration_Ms
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Experiment_Name import Safe_Str__Lab__Experiment_Name
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id         import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Experiment__Metadata import Schema__Lab__Experiment__Metadata
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Run__Result         import Schema__Lab__Run__Result
from sgraph_ai_service_playwright__cli.aws.lab.service.experiments.Lab__Experiment      import Lab__Experiment
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                      import Lab__Ledger
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Runner                      import Lab__Runner
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Dispatcher import Lab__Teardown__Dispatcher
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__R53      import Lab__Teardown__R53
from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Timing__Sample import List__Schema__Lab__Timing__Sample
from datetime import datetime, timezone


class _Fake_Teardown__R53(Lab__Teardown__R53):
    def teardown(self, entry) -> bool:
        return True


class _Noop__Experiment(Lab__Experiment):

    def execute(self) -> Schema__Lab__Run__Result:
        return Schema__Lab__Run__Result(
            run_id      = Safe_Str__Lab__Run_Id(self.runner.run_id if self.runner else ''),
            status      = Enum__Lab__Experiment__Status.OK,
            started_at  = datetime.now(timezone.utc).isoformat(),
            finished_at = datetime.now(timezone.utc).isoformat(),
            duration_ms = Safe_Int__Duration_Ms(10),
            samples     = List__Schema__Lab__Timing__Sample(),
            error       = '',
            notes       = 'no-op',
        )

    def metadata(self) -> Schema__Lab__Experiment__Metadata:
        return Schema__Lab__Experiment__Metadata(
            name        = Safe_Str__Lab__Experiment_Name('noop'),
            description = 'no-op test experiment',
            tier        = Enum__AWS__Mutation__Tier.READ_ONLY,
            agent       = 'test',
            phase       = 'P0',
        )


def _make_runner(tmp_dir: str) -> Lab__Runner:
    ledger     = Lab__Ledger(ledger_path=os.path.join(tmp_dir, 'ledger.jsonl'))
    ledger.setup()
    dispatcher = Lab__Teardown__Dispatcher(r53=_Fake_Teardown__R53())
    dispatcher.cf      = None
    dispatcher.lambda_ = None
    dispatcher.acm     = None
    dispatcher.ec2     = None
    dispatcher.ssm     = None
    dispatcher.iam     = None
    runner = Lab__Runner(ledger=ledger, dispatcher=dispatcher)
    runner.setup()
    return runner


class test_Lab__Runner__In_Memory(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.runner  = _make_runner(self.tmp_dir)

    def test_1__run_id_set_after_setup(self):
        assert self.runner.run_id != ''
        assert '__' in self.runner.run_id                                           # <ts>__<nonce>

    def test_2__noop_experiment_returns_ok(self):
        result = self.runner.run(_Noop__Experiment())
        assert result.status == Enum__Lab__Experiment__Status.OK
        assert result.notes == 'no-op'

    def test_3__create_and_register_writes_ledger_before_factory(self):
        call_order = []

        def factory():
            ledger_state = self.runner.ledger.all_entries()
            call_order.append(('factory', len(ledger_state)))                      # ledger must already have 1 entry
            return 'resource-handle'

        self.runner.create_and_register(
            resource_type = Enum__Lab__Resource_Type.R53_RECORD,
            resource_id   = 'ZONE1/test.example.com/A',
            experiment    = 'test',
            factory       = factory,
        )

        assert call_order[0] == ('factory', 1)                                     # entry was written before factory

    def test_4__failed_factory_marks_entry_failed(self):
        def bad_factory():
            raise RuntimeError('simulated failure')

        with self.assertRaises(RuntimeError):
            self.runner.create_and_register(
                resource_type = Enum__Lab__Resource_Type.R53_RECORD,
                resource_id   = 'ZONE1/bad.example.com/A',
                experiment    = 'test',
                factory       = bad_factory,
            )

        entries = self.runner.ledger.all_entries()
        assert entries[0].state == Enum__Lab__Entry__State.FAILED

    def test_5__run_id_injected_into_experiment(self):
        experiment = _Noop__Experiment()
        result     = self.runner.run(experiment)
        assert str(result.run_id) == self.runner.run_id
