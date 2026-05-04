# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Ollama__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.ollama.service.Ollama__User_Data__Builder import Ollama__User_Data__Builder


class test_Ollama__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Ollama__User_Data__Builder()
        self.out     = self.builder.render(stack_name='test-ol', region='eu-west-2')

    def test_render__shebang_and_strict_mode(self):
        assert '#!/usr/bin/env bash' in self.out
        assert 'set -euo pipefail'   in self.out

    def test_render__base_section(self):
        assert 'dnf install' in self.out

    def test_render__nvidia_drivers_present_by_default(self):
        assert 'nvidia-driver'   in self.out
        assert 'cuda-toolkit'    in self.out
        assert 'modprobe nvidia' in self.out

    def test_render__nvidia_drivers_absent_when_cpu_only(self):
        out = self.builder.render(stack_name='test-ol', region='eu-west-2', gpu_required=False)
        assert 'nvidia-driver' not in out
        assert 'cuda-toolkit'  not in out

    def test_render__ollama_install(self):
        assert 'ollama.com/install.sh' in self.out
        assert 'systemctl enable'      in self.out
        assert 'ollama'                in self.out

    def test_render__ollama_waits_for_ready(self):
        assert '/api/tags' in self.out

    def test_render__pull_on_boot_default(self):
        assert 'ollama pull' in self.out

    def test_render__pull_skipped_when_false(self):
        out = self.builder.render(stack_name='test-ol', region='eu-west-2', pull_on_boot=False)
        assert 'ollama pull' not in out

    def test_render__model_name_in_pull(self):
        out = self.builder.render(stack_name='test-ol', region='eu-west-2',
                                  model_name='llama3.3', pull_on_boot=True)
        assert 'ollama pull llama3.3' in out

    def test_render__shutdown_present_when_max_hours_gt_0(self):
        out = self.builder.render(stack_name='test-ol', region='eu-west-2', max_hours=4)
        assert 'systemd-run'    in out
        assert '--on-active=4h' in out

    def test_render__no_shutdown_when_max_hours_0(self):
        out = self.builder.render(stack_name='test-ol', region='eu-west-2', max_hours=0)
        assert 'systemd-run' not in out

    def test_render__no_nginx(self):
        assert 'nginx' not in self.out

    def test_render__footer(self):
        assert 'boot complete' in self.out
