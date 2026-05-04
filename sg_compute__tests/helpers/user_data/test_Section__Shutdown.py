# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Shutdown
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Shutdown import Section__Shutdown


class test_Section__Shutdown(TestCase):

    def test_render__systemd_run(self):
        out = Section__Shutdown().render(max_hours=1)
        assert 'systemd-run' in out
        assert '--on-active=1h' in out
        assert 'shutdown -h now' in out

    def test_render__custom_hours(self):
        out = Section__Shutdown().render(max_hours=4)
        assert '--on-active=4h' in out
