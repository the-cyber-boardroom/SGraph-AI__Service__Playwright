# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Capture__Writer
# Uses a temporary directory as capture root; no mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import stat
import tempfile
from pathlib                                                                     import Path
from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer import Bedrock__Capture__Writer


class test_Bedrock__Capture__Writer(TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.writer  = Bedrock__Capture__Writer(root=self._tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ── capture_root ──────────────────────────────────────────────────────────

    def test__capture_root__returns_path(self):
        assert isinstance(self.writer.capture_root(), Path)

    def test__capture_root__matches_tmp(self):
        assert str(self.writer.capture_root()) == self._tmpdir

    # ── write_chat ────────────────────────────────────────────────────────────

    def test__write_chat__creates_file(self):
        path = self.writer.write_chat('2026-05-17', 'abc123', {'text': 'hello'})
        assert path.exists()

    def test__write_chat__correct_layout(self):
        path = self.writer.write_chat('2026-05-17', 'run1', {'x': 1})
        assert 'chat'        in str(path)
        assert '2026-05-17'  in str(path)
        assert 'run1.json'   in str(path)

    def test__write_chat__json_content_correct(self):
        payload = {'prompt': 'hello', 'response_text': 'world'}
        path    = self.writer.write_chat('2026-05-17', 'r2', payload)
        loaded  = json.loads(path.read_text())
        assert loaded['prompt']        == 'hello'
        assert loaded['response_text'] == 'world'

    def test__write_chat__permissions_are_0600(self):
        path = self.writer.write_chat('2026-05-17', 'r3', {'k': 'v'})
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600

    # ── write_agent_definition ────────────────────────────────────────────────

    def test__write_agent_definition__creates_file(self):
        path = self.writer.write_agent_definition('researcher', {'agent_id': 'abc'})
        assert path.exists()
        assert path.name == 'definition.json'

    def test__write_agent_definition__correct_layout(self):
        path = self.writer.write_agent_definition('researcher', {})
        assert 'agents'     in str(path)
        assert 'researcher' in str(path)

    # ── write_agent_session ───────────────────────────────────────────────────

    def test__write_agent_session__creates_file(self):
        path = self.writer.write_agent_session('researcher', 'sess1', {'trace': []})
        assert path.exists()
        assert path.name == 'trace.json'

    # ── write_agent_memory ────────────────────────────────────────────────────

    def test__write_agent_memory__creates_file(self):
        path = self.writer.write_agent_memory('researcher', 'short', 'snap1', {'data': 'x'})
        assert path.exists()
        assert 'memory' in str(path)
        assert 'short'  in str(path)

    # ── write_browser_action ──────────────────────────────────────────────────

    def test__write_browser_action__creates_file(self):
        path = self.writer.write_browser_action('sess-browser-1', {'action': 'navigate'})
        assert path.exists()
        assert 'browser'  in str(path)

    # ── write_code_run ────────────────────────────────────────────────────────

    def test__write_code_run__creates_file(self):
        path = self.writer.write_code_run('sess-code-1', {'code': 'print(1)'})
        assert path.exists()
        assert 'code-interpreter' in str(path)

    # ── permissions for all types ─────────────────────────────────────────────

    def test__write_json__file_permissions_always_0600(self):
        path = self.writer.chat_path('2026-05-17', 'perm-test')
        self.writer.write_json(path, {'ok': True})
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600
