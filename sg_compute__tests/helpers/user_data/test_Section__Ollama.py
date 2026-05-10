# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Ollama
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Ollama import Section__Ollama


class test_Section__Ollama(TestCase):

    def setUp(self):
        self.section = Section__Ollama()

    def test_render__without_expose_api__no_override(self):
        out = self.section.render(model_name='gpt-oss:20b', expose_api=False)
        assert '0.0.0.0:11434' not in out

    def test_render__with_expose_api__writes_systemd_drop_in(self):
        out = self.section.render(model_name='gpt-oss:20b', expose_api=True)
        assert 'OLLAMA_HOST=0.0.0.0:11434' in out
        assert 'systemctl daemon-reload'   in out

    def test_render__pulls_model(self):
        out = self.section.render(model_name='gpt-oss:20b')
        assert 'ollama pull gpt-oss:20b' in out

    def test_render__skip_pull_when_disabled(self):
        out = self.section.render(model_name='gpt-oss:20b', pull_on_boot=False)
        assert 'ollama pull gpt-oss:20b' not in out
        assert 'skipping pull' in out

    def test_render__waits_for_api_ready(self):
        out = self.section.render(model_name='gpt-oss:20b')
        assert '/api/tags' in out
