# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Audit__Log (v0.2.28 — rich event fields, file mode, rotation)
# Uses a temp file path — never touches ~/.sg/audit.jsonl in tests.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import stat
import tempfile
from pathlib  import Path
from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action  import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.service.Audit__Log         import Audit__Log, ROTATION_SIZE_BYTES


def _audit(tmp_dir: str) -> Audit__Log:
    path = str(Path(tmp_dir) / 'audit.jsonl')
    return Audit__Log(audit_file=path)


class test_Audit__Log__log(TestCase):

    def test__log_writes_event_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            event  = audit.log(Enum__Audit__Action.ADD, role='admin')
            assert str(event.action) == 'add'
            assert str(event.role)   == 'admin'

    def test__log_appends_multiple_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.ADD,    role='admin')
            audit.log(Enum__Audit__Action.REMOVE, role='admin')
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
            audit.log(Enum__Audit__Action.STATUS)
            events = audit.read_all()
            assert events[0]['role'] == ''

    def test__secret_values_not_in_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.ADD, role='admin', command_args='credentials add admin <redacted> <redacted>')
            path   = Path(tmp) / 'audit.jsonl'
            raw    = path.read_text()
            assert 'secret' not in raw.lower()

    def test__log_new_fields_are_serialised(self):           # v0.2.28: all fields written to JSONL
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(
                Enum__Audit__Action.ASSUME,
                role           = 'admin',
                identity_arn   = 'arn:aws:sts::123456789012:assumed-role/sg-admin/sg-admin-1234-abcd',
                session_id     = 'sg-admin-1234-abcdef12',
                session_expiry = '2026-05-17T12:00:00Z',
                command_args   = 'aws lambda waker info',
                resolved_via   = ['default', 'admin'],
                duration_ms    = 123,
                success        = True,
                error          = '',
            )
            events = audit.read_all()
            assert len(events) == 1
            e = events[0]
            assert 'identity_arn'   in e
            assert 'session_id'     in e
            assert 'session_expiry' in e
            assert 'resolved_via'   in e
            assert 'duration_ms'    in e
            assert 'success'        in e
            assert 'error'          in e
            assert e['identity_arn']   == 'arn:aws:sts::123456789012:assumed-role/sg-admin/sg-admin-1234-abcd'
            assert e['resolved_via']   == ['default', 'admin']
            assert e['duration_ms']    == 123
            assert e['success']        is True

    def test__log_duration_ms_defaults_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.LIST)
            events = audit.read_all()
            assert events[0]['duration_ms'] == 0

    def test__log_resolved_via_defaults_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.LIST, role='dev')
            events = audit.read_all()
            assert events[0]['resolved_via'] == []

    def test__log_success_defaults_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            events = audit.read_all()
            assert events[0]['success'] is True


class test_Audit__Log__file_mode(TestCase):

    def test__file_created_with_mode_0600(self):            # §3.7 invariant 5
        with tempfile.TemporaryDirectory() as tmp:
            audit = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            path  = Path(tmp) / 'audit.jsonl'
            mode  = path.stat().st_mode & 0o777
            assert mode == 0o600

    def test__widened_mode_is_reset_on_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            path  = Path(tmp) / 'audit.jsonl'
            os.chmod(path, 0o644)                            # widen the mode
            audit.log(Enum__Audit__Action.STATUS)
            mode  = path.stat().st_mode & 0o777
            assert mode == 0o600                             # reset back to 0600


class test_Audit__Log__rotation(TestCase):

    def test__rotation_occurs_at_50mb(self):                # single roll: audit.jsonl → audit.jsonl.1
        with tempfile.TemporaryDirectory() as tmp:
            audit    = _audit(tmp)
            path     = Path(tmp) / 'audit.jsonl'
            rotated  = path.with_suffix('.jsonl.1')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'x' * ROTATION_SIZE_BYTES)    # fake 50 MB file
            audit.log(Enum__Audit__Action.STATUS)
            assert rotated.exists()                          # old file rotated
            assert path.exists()                             # new file created by append

    def test__no_rotation_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit   = _audit(tmp)
            path    = Path(tmp) / 'audit.jsonl'
            rotated = path.with_suffix('.jsonl.1')
            audit.log(Enum__Audit__Action.STATUS)
            assert not rotated.exists()


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
                audit.log(action, role='dev')
            events = audit.read_all()
            assert len(events) == 3


class test_Audit__Log__tail(TestCase):

    def test__tail_returns_last_n_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            for i in range(5):
                audit.log(Enum__Audit__Action.LIST, command_args=f'event-{i}')
            tail   = audit.tail(3)
            assert len(tail) == 3
            assert tail[-1]['command_args'] == 'event-4'

    def test__tail_with_n_larger_than_log_returns_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit  = _audit(tmp)
            audit.log(Enum__Audit__Action.STATUS)
            audit.log(Enum__Audit__Action.STATUS)
            tail   = audit.tail(100)
            assert len(tail) == 2
