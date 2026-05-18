# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Sweeper
# In-memory setup; only resources with all 3 required tags + expired TTL swept.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State        import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type       import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id   import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id     import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry   import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                  import Lab__Ledger
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Sweeper                 import Lab__Sweeper
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Dispatcher import Lab__Teardown__Dispatcher
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__R53  import Lab__Teardown__R53


def _expired_entry(entry_id: str = 'a' * 32) -> Schema__Lab__Ledger__Entry:
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return Schema__Lab__Ledger__Entry(
        entry_id      = Safe_Str__Lab__Entry_Id(entry_id),
        run_id        = Safe_Str__Lab__Run_Id('2026-05-18T00:00:00Z__aaaaaa'),
        resource_type = Enum__Lab__Resource_Type.R53_RECORD,
        resource_id   = Safe_Str__AWS__ARN('ZONE1/test.example.com/A'),
        region        = Safe_Str__AWS__Region('us-east-1'),
        created_at    = past,
        expires_at    = past,
        state         = Enum__Lab__Entry__State.PENDING,
        experiment    = 'test',
        extra         = '',
    )


def _fresh_entry(entry_id: str = 'b' * 32) -> Schema__Lab__Ledger__Entry:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return Schema__Lab__Ledger__Entry(
        entry_id      = Safe_Str__Lab__Entry_Id(entry_id),
        run_id        = Safe_Str__Lab__Run_Id('2026-05-18T00:00:00Z__bbbbbb'),
        resource_type = Enum__Lab__Resource_Type.R53_RECORD,
        resource_id   = Safe_Str__AWS__ARN('ZONE2/other.example.com/A'),
        region        = Safe_Str__AWS__Region('us-east-1'),
        created_at    = (datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        expires_at    = future,
        state         = Enum__Lab__Entry__State.PENDING,
        experiment    = 'test',
        extra         = '',
    )


class _Fake_Teardown__R53(Lab__Teardown__R53):
    deleted: list = None

    def __init__(self):
        super().__init__()
        self.deleted = []

    def teardown(self, entry) -> bool:
        self.deleted.append(str(entry.entry_id))
        return True


class test_Lab__Sweeper(TestCase):

    def setUp(self):
        self.tmp_dir  = tempfile.mkdtemp()
        self.ledger   = Lab__Ledger(ledger_path=os.path.join(self.tmp_dir, 'ledger.jsonl'))
        self.ledger.setup()
        self.fake_r53 = _Fake_Teardown__R53()
        dispatcher    = Lab__Teardown__Dispatcher(r53=self.fake_r53)
        self.sweeper  = Lab__Sweeper(ledger=self.ledger, dispatcher=dispatcher)

    def test_1__empty_ledger_returns_zero_leaked(self):
        report = self.sweeper.sweep(apply=False)
        assert report.leaked  == 0
        assert report.scanned == 0

    def test_2__expired_entry_is_leaked(self):
        self.ledger.append(_expired_entry())
        report = self.sweeper.sweep(apply=False)
        assert report.scanned == 1
        assert report.leaked  == 1
        assert report.deleted == 0
        assert report.dry_run is True

    def test_3__fresh_entry_is_not_leaked(self):
        self.ledger.append(_fresh_entry())
        report = self.sweeper.sweep(apply=False)
        assert report.leaked == 0

    def test_4__apply_deletes_expired_entry(self):
        entry = _expired_entry()
        self.ledger.append(entry)
        report = self.sweeper.sweep(apply=True)
        assert report.leaked  == 1
        assert report.deleted == 1
        assert str(entry.entry_id) in self.fake_r53.deleted

    def test_5__fresh_entry_not_deleted_even_with_apply(self):
        self.ledger.append(_fresh_entry())
        report = self.sweeper.sweep(apply=True)
        assert report.deleted == 0
        assert self.fake_r53.deleted == []

    def test_6__only_already_deleted_entries_excluded(self):
        expired = _expired_entry('a' * 32)
        self.ledger.append(expired)
        self.ledger.update_state(str(expired.entry_id), Enum__Lab__Entry__State.DELETED)
        report = self.sweeper.sweep(apply=False)
        assert report.scanned == 0                                                 # deleted entries not in pending_entries()
