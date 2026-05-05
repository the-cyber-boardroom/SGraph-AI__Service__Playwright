# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Shell__Executor + Safe_Str__Shell__Command
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sg_compute.host_plane.shell.primitives.Safe_Str__Shell__Command        import Safe_Str__Shell__Command
from sg_compute.host_plane.shell.schemas.Schema__Shell__Execute__Request    import Schema__Shell__Execute__Request
from sg_compute.host_plane.shell.schemas.Schema__Shell__Execute__Response   import Schema__Shell__Execute__Response
from sg_compute.host_plane.shell.service.Shell__Executor                    import Shell__Executor


class test_Safe_Str__Shell__Command(TestCase):

    def test_allowlisted_command__accepted(self):
        cmd = Safe_Str__Shell__Command('df -h')
        assert str(cmd) == 'df -h'

    def test_docker_ps__accepted(self):
        cmd = Safe_Str__Shell__Command('docker ps')
        assert str(cmd) == 'docker ps'

    def test_uname_r__accepted(self):
        cmd = Safe_Str__Shell__Command('uname -r')
        assert str(cmd) == 'uname -r'

    def test_systemctl_status__accepted(self):
        cmd = Safe_Str__Shell__Command('systemctl status docker')
        assert str(cmd) == 'systemctl status docker'

    def test_disallowed_command__raises(self):
        with pytest.raises(ValueError, match='not in allowlist'):
            Safe_Str__Shell__Command('rm -rf /')

    def test_empty_command__allowed_as_default(self):
        cmd = Safe_Str__Shell__Command('')       # Type_Safe default construction must not raise
        assert str(cmd) == ''

    def test_arbitrary_command__raises(self):
        with pytest.raises(ValueError, match='not in allowlist'):
            Safe_Str__Shell__Command('cat /etc/passwd')

    def test_unrestricted_mode__skips_allowlist(self):
        import os
        os.environ['SG_SHELL_UNRESTRICTED'] = '1'
        try:
            cmd = Safe_Str__Shell__Command('docker images')
            assert str(cmd) == 'docker images'
        finally:
            del os.environ['SG_SHELL_UNRESTRICTED']

    def test_unrestricted_mode__off_by_default(self):
        import os
        os.environ.pop('SG_SHELL_UNRESTRICTED', None)
        with pytest.raises(ValueError, match='not in allowlist'):
            Safe_Str__Shell__Command('docker images')


class test_Shell__Executor(TestCase):

    def setUp(self):
        self.executor = Shell__Executor()

    def test_df_h__returns_output(self):
        req    = Schema__Shell__Execute__Request(command=Safe_Str__Shell__Command('df -h'))
        result = self.executor.execute(req)
        assert isinstance(result, Schema__Shell__Execute__Response)
        assert result.exit_code == 0
        assert result.timed_out is False
        assert '/dev/' in result.stdout or 'Filesystem' in result.stdout

    def test_free_m__returns_output(self):
        req    = Schema__Shell__Execute__Request(command=Safe_Str__Shell__Command('free -m'))
        result = self.executor.execute(req)
        assert result.exit_code == 0
        assert result.stdout != ''

    def test_uptime__returns_output(self):
        req    = Schema__Shell__Execute__Request(command=Safe_Str__Shell__Command('uptime'))
        result = self.executor.execute(req)
        assert result.exit_code == 0

    def test_duration__is_positive(self):
        req    = Schema__Shell__Execute__Request(command=Safe_Str__Shell__Command('uptime'))
        result = self.executor.execute(req)
        assert result.duration > 0

    def test_timeout__enforced(self):
        req = Schema__Shell__Execute__Request(
            command = Safe_Str__Shell__Command('df -h'),
            timeout = 0,                                    # 0 → clamped to 30 by executor
        )
        result = self.executor.execute(req)
        assert isinstance(result, Schema__Shell__Execute__Response)

    def test_working_dir__accepted(self):
        req    = Schema__Shell__Execute__Request(
            command     = Safe_Str__Shell__Command('df -h'),
            working_dir = '/tmp',
        )
        result = self.executor.execute(req)
        assert result.exit_code == 0
