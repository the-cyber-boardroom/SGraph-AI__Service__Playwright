# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Node
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Node import Section__Node


class test_Section__Node(TestCase):

    def test_render__default_major_24(self):
        out = Section__Node().render()
        assert 'setup_24.x' in out
        assert 'Node.js 24' in out

    def test_render__custom_major(self):
        out = Section__Node().render(node_major=20)
        assert 'setup_20.x' in out

    def test_render__installs_pnpm(self):
        out = Section__Node().render()
        assert 'pnpm' in out
