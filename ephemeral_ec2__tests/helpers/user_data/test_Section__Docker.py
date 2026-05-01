# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — Section__Docker
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from ephemeral_ec2.helpers.user_data.Section__Docker import Section__Docker


class test_Section__Docker(TestCase):

    def test_render__installs_docker(self):
        out = Section__Docker().render()
        assert 'dnf install -y docker' in out

    def test_render__enables_service(self):
        out = Section__Docker().render()
        assert 'systemctl enable --now docker' in out

    def test_render__returns_str(self):
        assert isinstance(Section__Docker().render(), str)
