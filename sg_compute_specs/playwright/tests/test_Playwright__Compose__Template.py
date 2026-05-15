# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Playwright__Compose__Template
# Pure rendering — no AWS, no network. Verifies the 2-container default and the
# 3-container --with-mitmproxy shapes, plus the interceptor toggle.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.playwright.service.Playwright__Compose__Template import Playwright__Compose__Template


ECR = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


class test_Playwright__Compose__Template(TestCase):

    def setUp(self):
        self.template = Playwright__Compose__Template()

    def test__default__two_containers(self):
        yaml = self.template.render(ecr_registry=ECR)
        assert 'host-plane'                              in yaml
        assert 'sg-playwright'                          in yaml
        assert 'agent-mitmproxy'                        not in yaml
        assert f'{ECR}/sgraph_ai_service_playwright_host:latest' in yaml
        assert f'{ECR}/diniscruz/sg-playwright:latest'  in yaml
        assert '"8000:8000"'                            in yaml
        assert 'sg-net'                                 in yaml

    def test__default__no_proxy_wiring(self):
        yaml = self.template.render(ecr_registry=ECR)
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL'       not in yaml
        assert 'depends_on'                             not in yaml

    def test__with_mitmproxy__three_containers(self):
        yaml = self.template.render(ecr_registry=ECR, with_mitmproxy=True)
        assert 'host-plane'                             in yaml
        assert 'sg-playwright'                          in yaml
        assert 'agent-mitmproxy'                        in yaml
        assert f'{ECR}/agent_mitmproxy:latest'          in yaml
        assert '"8001:8000"'                            in yaml

    def test__with_mitmproxy__proxy_wiring_present(self):
        yaml = self.template.render(ecr_registry=ECR, with_mitmproxy=True)
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL:   http://agent-mitmproxy:8080' in yaml
        assert "SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS: 'true'"                      in yaml
        assert 'depends_on'                             in yaml

    def test__interceptor_toggle(self):
        without = self.template.render(ecr_registry=ECR, with_mitmproxy=True, with_intercept=False)
        assert 'AGENT_MITMPROXY__INTERCEPTOR_PATH'      not in without
        assert '/app/interceptors'                      not in without

        with_it = self.template.render(ecr_registry=ECR, with_mitmproxy=True, with_intercept=True)
        assert 'AGENT_MITMPROXY__INTERCEPTOR_PATH: /app/interceptors/active.py' in with_it
        assert '/opt/sg-playwright/interceptors:/app/interceptors:ro'          in with_it

    def test__interceptor_ignored_without_mitmproxy(self):
        yaml = self.template.render(ecr_registry=ECR, with_mitmproxy=False, with_intercept=True)
        assert 'agent-mitmproxy'                        not in yaml          # no mitmproxy → no interceptor

    def test__image_tag_threaded(self):
        yaml = self.template.render(ecr_registry=ECR, with_mitmproxy=True, image_tag='v1.2.3')
        assert f'{ECR}/diniscruz/sg-playwright:v1.2.3'   in yaml
        assert f'{ECR}/agent_mitmproxy:v1.2.3'           in yaml
