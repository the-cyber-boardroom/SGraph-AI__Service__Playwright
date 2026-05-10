# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Claude_Launch
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Claude_Launch import Section__Claude_Launch


class test_Section__Claude_Launch(TestCase):

    def setUp(self):
        self.section = Section__Claude_Launch()

    def test_render__empty_when_disabled(self):
        assert self.section.render(model_name='gpt-oss:20b', with_claude=False) == ''

    def test_render__creates_tmux_session_when_enabled(self):
        out = self.section.render(model_name='gpt-oss:20b', with_claude=True)
        assert 'tmux new-session'  in out
        assert 'gpt-oss:20b'       in out
        assert 'tmux attach -t claude' in out
