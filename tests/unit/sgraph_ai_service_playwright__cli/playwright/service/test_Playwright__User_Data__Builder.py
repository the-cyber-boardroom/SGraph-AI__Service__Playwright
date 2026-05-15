# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__User_Data__Builder
# Pure rendering — no AWS, no network calls. Verifies all 7 boot sections
# are present and the --with-mitmproxy toggle works.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.playwright.service.Playwright__User_Data__Builder import (
    Playwright__User_Data__Builder, PLACEHOLDERS, LOG_FILE, COMPOSE_FILE,
    INTERCEPTOR_FILE, NOOP_INTERCEPTOR)


FAKE_COMPOSE = 'services:\n  sg-playwright:\n    image: diniscruz/sg-playwright:latest\n'
FAKE_REGISTRY = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


class test_Playwright__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Playwright__User_Data__Builder()

    def _render(self, **kw):
        defaults = dict(stack_name='playwright-quiet-fermi', region='eu-west-2',
                        compose_yaml=FAKE_COMPOSE, registry=FAKE_REGISTRY)
        defaults.update(kw)
        return self.builder.render(**defaults)

    # ── section 1: header ────────────────────────────────────────────────────
    def test__header_section_present(self):
        ud = self._render()
        assert '#!/usr/bin/env bash'              in ud
        assert 'set -euo pipefail'               in ud
        assert LOG_FILE                          in ud

    # ── section 2: docker install ────────────────────────────────────────────
    def test__docker_install_section_present(self):
        ud = self._render()
        assert 'dnf install -y docker'           in ud
        assert 'systemctl enable --now docker'   in ud
        assert 'docker-compose-linux-x86_64'     in ud

    # ── section 3: layout ────────────────────────────────────────────────────
    def test__layout_mkdir_present(self):
        ud = self._render()
        assert 'mkdir -p /opt/sg-playwright'     in ud

    # ── section 4: intercept script (with_mitmproxy only) ───────────────────
    def test__no_interceptor_section_when_mitmproxy_off(self):
        ud = self._render(with_mitmproxy=False)
        assert INTERCEPTOR_FILE                  not in ud

    def test__interceptor_section_present_with_mitmproxy(self):
        ud = self._render(with_mitmproxy=True)
        assert INTERCEPTOR_FILE                  in ud

    def test__noop_interceptor_written_when_no_script(self):
        ud = self._render(with_mitmproxy=True, intercept_script='')
        assert 'def request(flow)'               in ud                          # noop content

    def test__custom_script_baked_in_when_provided(self):
        script = '# custom\ndef request(flow): flow.kill()\n'
        ud = self._render(with_mitmproxy=True, intercept_script=script)
        assert '# custom'                        in ud
        assert 'flow.kill()'                     in ud

    # ── section 5: compose ───────────────────────────────────────────────────
    def test__compose_heredoc_present(self):
        ud = self._render()
        assert COMPOSE_FILE                      in ud
        assert FAKE_COMPOSE                      in ud
        assert 'docker compose up -d'            in ud

    # ── section 6: host control plane ────────────────────────────────────────
    def test__host_control_section_present(self):
        ud = self._render()
        assert 'sp-host-control'                 in ud
        assert '--privileged'                    in ud
        assert '/var/run/docker.sock'            in ud
        assert '19009:8000'                      in ud
        assert FAKE_REGISTRY                     in ud
        assert 'sgraph_ai_service_playwright_host:latest' in ud

    # ── section 7: shutdown timer ────────────────────────────────────────────
    def test__shutdown_section_present_when_max_hours_nonzero(self):
        ud = self._render(max_hours=2)
        assert 'systemd-run'                     in ud
        assert '7200'                            in ud                          # 2h in seconds
        assert 'auto-terminate'                  in ud.lower()

    def test__shutdown_section_absent_when_max_hours_zero(self):
        ud = self._render(max_hours=0)
        assert 'systemd-run'                     not in ud

    # ── stack_name + region baked in ─────────────────────────────────────────
    def test__stack_name_and_region_baked_in(self):
        ud = self._render(stack_name='playwright-my-stack', region='us-east-1')
        assert "STACK_NAME='playwright-my-stack'" in ud
        assert "REGION='us-east-1'"               in ud

    # ── PLACEHOLDERS constant is locked ──────────────────────────────────────
    def test__placeholders_constant_is_locked(self):
        assert 'stack_name'           in PLACEHOLDERS
        assert 'region'               in PLACEHOLDERS
        assert 'log_file'             in PLACEHOLDERS
        assert 'compose_file'         in PLACEHOLDERS
        assert 'compose_yaml'         in PLACEHOLDERS
        assert 'interceptor_section'  in PLACEHOLDERS
        assert 'host_control_section' in PLACEHOLDERS
        assert 'shutdown_section'     in PLACEHOLDERS


# Simpler check — the PLACEHOLDERS tuple is the authority
class test_PLACEHOLDERS(TestCase):

    def test__all_placeholders_present_in_render_output(self):
        ud = Playwright__User_Data__Builder().render(
            stack_name='playwright-x', region='eu-west-2',
            compose_yaml='services: {}\n', registry='reg.example.com',
            max_hours=1)
        assert 'playwright-x'     in ud
        assert 'eu-west-2'        in ud
        assert LOG_FILE           in ud
        assert COMPOSE_FILE       in ud
        assert 'docker compose'   in ud
