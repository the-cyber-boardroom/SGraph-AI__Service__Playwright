# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Ledger
# Round-trip write/read; partial-write recovery; concurrent-writer file-lock.
# ═══════════════════════════════════════════════════════════════════════════════

import concurrent.futures
import os
import tempfile
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State        import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type       import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id   import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id     import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry   import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                  import Lab__Ledger


def _make_entry(run_id='2026-05-18T00:00:00Z__abc123', entry_id='aabbccdd11223344aabbccdd11223344') -> Schema__Lab__Ledger__Entry:
    return Schema__Lab__Ledger__Entry(
        entry_id      = Safe_Str__Lab__Entry_Id(entry_id),
        run_id        = Safe_Str__Lab__Run_Id(run_id),
        resource_type = Enum__Lab__Resource_Type.R53_RECORD,
        resource_id   = Safe_Str__AWS__ARN('ZONEABC/test.example.com/A'),
        region        = Safe_Str__AWS__Region('us-east-1'),
        created_at    = '2026-05-18T00:00:00Z',
        expires_at    = '2026-05-18T01:00:00Z',
        state         = Enum__Lab__Entry__State.PENDING,
        experiment    = 'test-experiment',
        extra         = '',
    )


class test_Lab__Ledger(TestCase):

    def setUp(self):
        self.tmp_dir  = tempfile.mkdtemp()
        self.ledger   = Lab__Ledger(ledger_path=os.path.join(self.tmp_dir, 'test-ledger.jsonl'))
        self.ledger.setup()

    def test_1__write_and_read_round_trip(self):
        entry = _make_entry()
        self.ledger.append(entry)

        all_entries = self.ledger.all_entries()
        assert len(all_entries) == 1
        got = all_entries[0]
        assert str(got.entry_id)      == str(entry.entry_id)
        assert str(got.run_id)        == str(entry.run_id)
        assert got.resource_type      == Enum__Lab__Resource_Type.R53_RECORD
        assert str(got.resource_id)   == 'ZONEABC/test.example.com/A'
        assert got.state              == Enum__Lab__Entry__State.PENDING
        assert got.experiment         == 'test-experiment'

    def test_2__multiple_entries_preserved(self):
        for i in range(5):
            entry = _make_entry(entry_id=f'a{i}' * 16)
            self.ledger.append(entry)
        assert len(self.ledger.all_entries()) == 5

    def test_3__update_state(self):
        entry = _make_entry()
        self.ledger.append(entry)

        updated = self.ledger.update_state(str(entry.entry_id), Enum__Lab__Entry__State.DELETED)
        assert updated is True

        all_entries = self.ledger.all_entries()
        assert all_entries[0].state == Enum__Lab__Entry__State.DELETED

    def test_4__entries_for_run(self):
        entry_a = _make_entry(run_id='2026-05-18T00:00:00Z__aaaa11', entry_id='a' * 32)
        entry_b = _make_entry(run_id='2026-05-18T00:00:00Z__bbbb22', entry_id='b' * 32)
        self.ledger.append(entry_a)
        self.ledger.append(entry_b)

        run_a_entries = self.ledger.entries_for_run('2026-05-18T00:00:00Z__aaaa11')
        assert len(run_a_entries) == 1
        assert str(run_a_entries[0].run_id) == '2026-05-18T00:00:00Z__aaaa11'

    def test_5__partial_write_recovery(self):
        ledger_path = self.ledger.ledger_path
        valid_line  = '{"entry_id":"aabbccdd11223344aabbccdd11223344","run_id":"2026-05-18T00:00:00Z__abc123","resource_type":"r53-record","resource_id":"","region":"","created_at":"","expires_at":"","state":"pending","experiment":"","extra":""}'
        with open(ledger_path, 'w') as fh:
            fh.write(valid_line + '\n')
            fh.write('CORRUPT_LINE_NOT_JSON\n')

        entries = self.ledger.all_entries()
        assert len(entries) == 1                                                    # corrupted line skipped

    def test_6__concurrent_writers_do_not_corrupt(self):
        def write_entry(i):
            ledger = Lab__Ledger(ledger_path=self.ledger.ledger_path)
            entry  = _make_entry(entry_id=f'{i:016x}{i:016x}')
            ledger.append(entry)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(write_entry, range(20)))

        entries = self.ledger.all_entries()
        assert len(entries) == 20                                                   # all 20 written without corruption

    def test_7__pending_entries_filter(self):
        entry_a = _make_entry(entry_id='a' * 32)
        entry_b = _make_entry(entry_id='b' * 32)
        self.ledger.append(entry_a)
        self.ledger.append(entry_b)
        self.ledger.update_state(str(entry_a.entry_id), Enum__Lab__Entry__State.DELETED)

        pending = self.ledger.pending_entries()
        assert len(pending) == 1
        assert str(pending[0].entry_id) == str(entry_b.entry_id)
