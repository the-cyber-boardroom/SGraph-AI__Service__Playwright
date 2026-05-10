# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Agent_Tools
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Agent_Tools import Section__Agent_Tools


class test_Section__Agent_Tools(TestCase):

    def test_render__installs_python_venv(self):
        out = Section__Agent_Tools().render()
        assert 'python3.13 -m venv' in out
        assert '/home/ec2-user/venvs/agent-tools' in out

    def test_render__installs_python313(self):
        out = Section__Agent_Tools().render()
        assert 'python3.13' in out

    def test_render__installs_required_libraries(self):
        out = Section__Agent_Tools().render()
        for lib in ('requests', 'httpx', 'rich'):
            assert lib in out

    def test_render__configures_logrotate(self):
        out = Section__Agent_Tools().render()
        assert '/etc/logrotate.d/sg-compute' in out
        assert '/var/log/sg-compute/' in out
