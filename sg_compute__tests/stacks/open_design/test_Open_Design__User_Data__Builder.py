# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Open_Design__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.open_design.service.Open_Design__User_Data__Builder import Open_Design__User_Data__Builder


class test_Open_Design__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Open_Design__User_Data__Builder()
        self.out     = self.builder.render(stack_name='test-stack', region='eu-west-2')

    def test_render__contains_base_sections(self):
        assert '#!/usr/bin/env bash' in self.out
        assert 'set -euo pipefail'   in self.out
        assert 'dnf install'         in self.out

    def test_render__contains_docker(self):
        assert 'docker'      in self.out
        assert 'systemctl'   in self.out

    def test_render__contains_node_and_pnpm(self):
        assert 'pnpm'       in self.out
        assert 'setup_24.x' in self.out

    def test_render__env_file_has_od_port(self):
        assert 'OD_PORT=7456' in self.out

    def test_render__clone_and_build_present_by_default(self):
        assert 'nexu-io/open-design' in self.out
        assert 'pnpm install'        in self.out

    def test_render__fast_boot_skips_clone(self):
        out = self.builder.render(stack_name='test-stack', region='eu-west-2', fast_boot=True)
        assert 'nexu-io/open-design' not in out
        assert 'pnpm install'         not in out

    def test_render__systemd_service(self):
        assert 'open-design.service' in self.out
        assert 'ExecStart'           in self.out

    def test_render__nginx_sse_safe(self):
        assert 'proxy_buffering' in self.out
        assert 'nginx:alpine'    in self.out

    def test_render__api_key_adds_anthropic_env_and_claude_cli(self):
        out = self.builder.render(stack_name='test-stack', region='eu-west-2', api_key='sk-test')
        assert 'ANTHROPIC_API_KEY=sk-test' in out
        assert '@anthropic-ai/claude-code' in out

    def test_render__no_api_key_omits_claude_cli(self):
        assert '@anthropic-ai/claude-code' not in self.out
        assert 'ANTHROPIC_API_KEY'          not in self.out

    def test_render__ollama_base_url_in_env(self):
        out = self.builder.render(stack_name='test-stack', region='eu-west-2',
                                  ollama_base_url='http://10.0.0.5:11434')
        assert 'OLLAMA_BASE_URL=http://10.0.0.5:11434' in out

    def test_render__shutdown_present_when_max_hours_gt_0(self):
        out = self.builder.render(stack_name='test-stack', region='eu-west-2', max_hours=2)
        assert 'systemd-run'      in out
        assert '--on-active=2h'   in out

    def test_render__no_shutdown_when_max_hours_0(self):
        out = self.builder.render(stack_name='test-stack', region='eu-west-2', max_hours=0)
        assert 'systemd-run' not in out

    def test_render__footer(self):
        assert 'boot complete' in self.out
