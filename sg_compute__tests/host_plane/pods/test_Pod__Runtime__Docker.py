# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Pod__Runtime__Docker (subprocess stubbed)
# The subprocess boundary is the narrow exception to the no-mocks rule.
# All other assertions check typed schema output.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest import TestCase
from unittest.mock import patch, MagicMock

from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request         import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Response        import Schema__Pod__Start__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response
from sg_compute.host_plane.pods.service.Pod__Runtime__Docker                import Pod__Runtime__Docker


def _proc(stdout='', stderr='', rc=0):
    m = MagicMock()
    m.stdout     = stdout
    m.stderr     = stderr
    m.returncode = rc
    return m


class test_Pod__Runtime__Docker(TestCase):

    def setUp(self):
        self.runtime = Pod__Runtime__Docker()

    # ── list ─────────────────────────────────────────────────────────────────

    def test_list__empty(self):
        with patch('subprocess.run', return_value=_proc(stdout='')):
            result = self.runtime.list()
        assert isinstance(result, Schema__Pod__List)
        assert result.count == 0
        assert list(result.pods) == []

    def test_list__one_pod(self):
        row = json.dumps({'Names': 'sp-playwright', 'Image': 'playwright:latest',
                          'Status': 'running', 'State': 'Up 2 hours', 'CreatedAt': '2026-05-01'})
        with patch('subprocess.run', return_value=_proc(stdout=row)):
            result = self.runtime.list()
        assert result.count == 1
        pod = list(result.pods)[0]
        assert isinstance(pod, Schema__Pod__Info)
        assert pod.name   == 'sp-playwright'
        assert pod.image  == 'playwright:latest'
        assert pod.status == 'running'

    def test_list__malformed_json_skipped(self):
        stdout = 'not-json\n' + json.dumps({'Names': 'ok', 'Image': 'img', 'Status': 's', 'State': 'st', 'CreatedAt': ''})
        with patch('subprocess.run', return_value=_proc(stdout=stdout)):
            result = self.runtime.list()
        assert result.count == 1

    # ── start ─────────────────────────────────────────────────────────────────

    def test_start__success(self):
        with patch('subprocess.run', return_value=_proc(stdout='abc1234567890\n')):
            result = self.runtime.start(Schema__Pod__Start__Request(
                name='mypod', image='myimage:latest'))
        assert isinstance(result, Schema__Pod__Start__Response)
        assert result.started      is True
        assert result.container_id == 'abc123456789'

    def test_start__failure(self):
        with patch('subprocess.run', return_value=_proc(stdout='', stderr='image not found', rc=1)):
            result = self.runtime.start(Schema__Pod__Start__Request(
                name='bad', image='nonexistent'))
        assert result.started is False
        assert 'image not found' in result.error

    # ── info ─────────────────────────────────────────────────────────────────

    def test_info__found(self):
        inspect_data = json.dumps([{
            'Name'  : '/sp-playwright',
            'Config': {'Image': 'playwright:latest', 'Labels': {}},
            'State' : {'Status': 'running', 'Running': True},
            'NetworkSettings': {'Ports': {'8000/tcp': [{'HostPort': '8000'}]}},
            'Created': '2026-05-01T00:00:00Z',
        }])
        with patch('subprocess.run', return_value=_proc(stdout=inspect_data)):
            result = self.runtime.info('sp-playwright')
        assert isinstance(result, Schema__Pod__Info)
        assert result.name   == 'sp-playwright'
        assert result.state  == 'Up'
        assert result.status == 'running'

    def test_info__not_found(self):
        with patch('subprocess.run', return_value=_proc(stdout='', rc=1)):
            result = self.runtime.info('nonexistent')
        assert result is None

    # ── stop / remove ─────────────────────────────────────────────────────────

    def test_stop__success(self):
        with patch('subprocess.run', return_value=_proc(rc=0)):
            result = self.runtime.stop('mypod')
        assert isinstance(result, Schema__Pod__Stop__Response)
        assert result.stopped is True

    def test_remove__success(self):
        with patch('subprocess.run', return_value=_proc(rc=0)):
            result = self.runtime.remove('mypod')
        assert result.removed is True
