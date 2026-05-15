# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Playwright__Service CLI surface
# Verifies cli_spec() shape, helper wiring, and user-data render structure
# (no AWS calls).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.service.Playwright__Service              import Playwright__Service
from sg_compute_specs.playwright.service.Playwright__User_Data__Builder   import Playwright__User_Data__Builder


ECR = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


class TestPlaywrightServiceCliSurface:

    def test_cli_spec_shape(self):
        spec = Playwright__Service().cli_spec()
        assert spec.spec_id               == 'playwright'
        assert spec.display_name          == 'Playwright'
        assert spec.default_instance_type == 't3.medium'
        assert spec.health_path           == '/health/status'
        assert spec.health_port           == 8000
        assert spec.health_scheme         == 'http'
        assert spec.create_request_cls.__name__ == 'Schema__Playwright__Create__Request'

    def test_setup_wires_helpers(self):
        svc = Playwright__Service().setup()
        assert svc.aws_client        is not None
        assert svc.user_data_builder is not None
        assert svc.mapper            is not None
        assert svc.ip_detector       is not None
        assert svc.name_gen          is not None
        assert svc.ami_helper        is not None

    def test_user_data_timer_before_dnf(self):
        user_data = Playwright__User_Data__Builder().render(
            stack_name='pw-test', region='eu-west-2', ecr_registry=ECR, api_key='k', max_hours=1)
        lines   = user_data.splitlines()
        timer_i = next(i for i, l in enumerate(lines) if 'systemd-run' in l)
        dnf_i   = next(i for i, l in enumerate(lines) if l.strip().startswith('dnf install'))
        assert timer_i < dnf_i, 'auto-terminate timer must appear before any dnf install'

    def test_user_data_key_sections(self):
        user_data = Playwright__User_Data__Builder().render(
            stack_name='pw-test', region='eu-west-2', ecr_registry=ECR, api_key='secret-key')
        assert 'dnf install -y docker'                in user_data
        assert 'docker compose'                       in user_data
        assert '/opt/sg-playwright/docker-compose.yml' in user_data
        assert '/opt/sg-playwright/.env'              in user_data
        assert 'FAST_API__AUTH__API_KEY__VALUE=secret-key' in user_data
        assert 'aws ecr get-login-password'           in user_data
        assert 'host-plane'                           in user_data
        assert 'sg-playwright'                        in user_data

    def test_user_data_default_no_mitmproxy(self):
        user_data = Playwright__User_Data__Builder().render(
            stack_name='pw-test', region='eu-west-2', ecr_registry=ECR, api_key='k')
        assert 'agent-mitmproxy'      not in user_data
        assert 'interceptors/active'  not in user_data

    def test_user_data_with_mitmproxy_and_interceptor(self):
        user_data = Playwright__User_Data__Builder().render(
            stack_name='pw-test', region='eu-west-2', ecr_registry=ECR, api_key='k',
            with_mitmproxy=True, intercept_script='def request(flow):\n    pass')
        assert 'agent-mitmproxy'                            in user_data
        assert '/opt/sg-playwright/interceptors/active.py'  in user_data
        assert 'def request(flow):'                         in user_data

    def test_user_data_no_shutdown_when_max_hours_zero(self):
        user_data = Playwright__User_Data__Builder().render(
            stack_name='pw-test', region='eu-west-2', ecr_registry=ECR, api_key='k', max_hours=0)
        assert 'systemd-run' not in user_data
