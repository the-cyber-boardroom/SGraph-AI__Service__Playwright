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
from sg_compute.host_plane.pods.schemas.Schema__Pod__Logs__Response         import Schema__Pod__Logs__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request         import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Response        import Schema__Pod__Start__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stats                  import Schema__Pod__Stats
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response
from sg_compute.host_plane.pods.service.Pod__Runtime__Docker                import Pod__Runtime__Docker, _parse_mb, _parse_percent


def _proc(stdout='', stderr='', rc=0):
    m = MagicMock()
    m.stdout     = stdout
    m.stderr     = stderr
    m.returncode = rc
    return m


class test_parse_helpers(TestCase):

    def test_parse_percent(self):
        assert _parse_percent('1.40%') == 1.4
        assert _parse_percent('0%')    == 0.0
        assert _parse_percent('100%')  == 100.0

    def test_parse_mb__mib(self):
        assert _parse_mb('48.2MiB') == 48.2

    def test_parse_mb__gib(self):
        assert _parse_mb('1GiB') == 1024.0

    def test_parse_mb__kb(self):
        assert _parse_mb('122kB') == round(122 / 1024, 1)

    def test_parse_mb__bytes(self):
        assert _parse_mb('0B') == 0.0

    def test_parse_mb__mb(self):
        assert _parse_mb('2.1MB') == 2.1


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

    # ── logs ─────────────────────────────────────────────────────────────────

    def test_logs__returns_content(self):
        log_output = 'line1\nline2\nline3\n'
        with patch('subprocess.run', return_value=_proc(stdout=log_output)):
            result = self.runtime.logs('mypod', tail=100)
        assert isinstance(result, Schema__Pod__Logs__Response)
        assert result.container == 'mypod'
        assert result.lines     == 3
        assert 'line1'           in result.content
        assert result.truncated is False

    def test_logs__not_found_returns_none(self):
        with patch('subprocess.run', return_value=_proc(stdout='', stderr='', rc=1)):
            result = self.runtime.logs('nonexistent')
        assert result is None

    def test_logs__truncated_when_at_tail_limit(self):
        lines = ['line'] * 10
        with patch('subprocess.run', return_value=_proc(stdout='\n'.join(lines))):
            result = self.runtime.logs('mypod', tail=10)
        assert result.truncated is True

    def test_logs__timestamps_flag(self):
        captured = {}
        def _fake_run(args, **kw):
            captured['args'] = args
            return _proc(stdout='ts line\n')
        with patch('subprocess.run', side_effect=_fake_run):
            self.runtime.logs('mypod', timestamps=True)
        assert '--timestamps' in captured['args']

    # ── stats ─────────────────────────────────────────────────────────────────

    def test_stats__parses_docker_output(self):
        stats_json = json.dumps({
            'Name': 'sp-playwright', 'CPUPerc': '1.40%', 'MemPerc': '4.71%',
            'MemUsage': '48.2MiB / 1GiB', 'NetIO': '122kB / 81.5kB',
            'BlockIO': '0B / 2.1MB', 'PIDs': '6',
        })
        with patch('subprocess.run', return_value=_proc(stdout=stats_json)):
            result = self.runtime.stats('sp-playwright')
        assert isinstance(result, Schema__Pod__Stats)
        assert result.container    == 'sp-playwright'
        assert result.cpu_percent  == 1.4
        assert result.mem_usage_mb == 48.2
        assert result.mem_limit_mb == 1024.0
        assert result.pids         == 6

    def test_stats__not_found_returns_none(self):
        with patch('subprocess.run', return_value=_proc(stdout='', rc=1)):
            result = self.runtime.stats('nonexistent')
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
