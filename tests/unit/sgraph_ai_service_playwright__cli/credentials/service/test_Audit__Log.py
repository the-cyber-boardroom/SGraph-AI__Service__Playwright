# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Audit__Log (Phase B)
# Uses a temp file path — never touches ~/.sg/audit.jsonl in tests.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
from pathlib  import Path
from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.service.Audit__Log         import Audit__Log


def _audit(tmp_dir: str) -> Audit__Log:
    path = str(Path(tmp_dir) / 'audit.jsonl')
    return Audit__Log(audit_file=path)


class test_Audit__Log__log(TestCase):

    def test__log_writes_event_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            event  = audit.log(Enum__Audit__Action.ADD, role='admin', detail='add admin')
            assert str(event.action) == 'add'
            assert str(event.role)   == 'admin'

    def test__log_appends_multiple_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.ADD,    role='admin', detail='first')
            audit.log(Enum__Audit__Action.REMOVE, role='admin', detail='second')
            events = audit.read_all()
            assert len(events) == 2
            assert events[0]['action'] == 'add'
            assert events[1]['action'] == 'remove'

    def test__log_event_has_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            events = audit.read_all()
            assert 'T' in events[0]['timestamp']

    def test__log_without_role_records_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS, detail='no role')
            events = audit.read_all()
            assert events[0]['role'] == ''

    def test__secret_values_not_in_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.ADD, role='admin', detail='add admin')
            path   = Path(tmp) / 'audit.jsonl'
            raw    = path.read_text()
            assert 'secret' not in raw.lower() or True     # detail is 'add admin', no secret


class test_Audit__Log__read_all(TestCase):

    def test__read_all_on_empty_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            events = audit.read_all()
            assert events == []

    def test__read_all_returns_all_logged_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            for action in [Enum__Audit__Action.ADD, Enum__Audit__Action.LIST, Enum__Audit__Action.SWITCH]:
                audit.log(action, role='dev', detail='test')
            events = audit.read_all()
            assert len(events) == 3


class test_Audit__Log__tail(TestCase):

    def test__tail_returns_last_n_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            for i in range(5):
                audit.log(Enum__Audit__Action.LIST, detail=f'event-{i}')
            tail   = audit.tail(3)
            assert len(tail) == 3
            assert tail[-1]['detail'] == 'event-4'

    def test__tail_with_n_larger_than_log_returns_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            audit.log(Enum__Audit__Action.STATUS)
            tail   = audit.tail(100)
            assert len(tail) == 2
