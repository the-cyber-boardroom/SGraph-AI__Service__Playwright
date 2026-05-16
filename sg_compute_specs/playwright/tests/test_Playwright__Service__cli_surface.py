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

    def test_stack_mapper_surfaces_api_key_from_tag(self):
        # Mirror vault-app's TAG_ACCESS_TOKEN pattern — the api_key is written
        # to the StackApiKey tag at create time and recovered for `info`.
        from sg_compute_specs.playwright.service.Playwright__Stack__Mapper import (
            Playwright__Stack__Mapper, TAG_API_KEY)
        info = Playwright__Stack__Mapper().to_info(
            {'InstanceId'    : 'i-fake'                                            ,
             'InstanceType'  : 't3.medium'                                         ,
             'ImageId'       : 'ami-x'                                             ,
             'State'         : {'Name': 'running'}                                 ,
             'PublicIpAddress': '10.0.0.1'                                         ,
             'SecurityGroups': [{'GroupId': 'sg-x'}]                               ,
             'Tags'          : [{'Key': 'StackName', 'Value': 'pw-test'           },
                                {'Key': TAG_API_KEY, 'Value': 'tk_abc123'         }]},
            'eu-west-2')
        assert info.api_key == 'tk_abc123'

    def test_render_info_surfaces_auth_helpers_when_api_key_present(self):
        # The three auth-helper rows (api-key, set-cookie-form, browser-auth
        # bookmarklet) appear iff api_key is non-empty.
        from io   import StringIO
        from rich.console import Console
        from sg_compute_specs.playwright.cli.Renderers           import render_playwright_info
        from sg_compute_specs.playwright.schemas.Schema__Playwright__Info import Schema__Playwright__Info

        info = Schema__Playwright__Info(
            instance_id='i-x', stack_name='pw-test', region='eu-west-2', state='running',
            public_ip='10.0.0.1', playwright_url='http://10.0.0.1:8000', api_key='tk_abc123')
        buf  = StringIO()
        render_playwright_info(info, Console(file=buf, highlight=False, force_terminal=False, width=200))
        out  = buf.getvalue()
        assert 'tk_abc123'              in out
        assert '/auth/set-cookie-form'  in out
        assert 'document.cookie'        in out
        assert 'X-API-Key=tk_abc123'    in out

    def test_render_info_no_auth_helpers_when_api_key_blank(self):
        from io   import StringIO
        from rich.console import Console
        from sg_compute_specs.playwright.cli.Renderers           import render_playwright_info
        from sg_compute_specs.playwright.schemas.Schema__Playwright__Info import Schema__Playwright__Info

        info = Schema__Playwright__Info(
            instance_id='i-x', stack_name='pw-test', region='eu-west-2', state='running',
            public_ip='10.0.0.1', playwright_url='http://10.0.0.1:8000', api_key='')
        buf  = StringIO()
        render_playwright_info(info, Console(file=buf, highlight=False, force_terminal=False, width=200))
        out  = buf.getvalue()
        # No api-key value; set-cookie-form and bookmarklet still show (they're
        # tied to playwright_url, with a YOUR_API_KEY placeholder).
        assert 'api-key'                not in out         # no value → row skipped
        assert '/auth/set-cookie-form'  in out             # still shown — useful as documentation
        assert 'YOUR_API_KEY'           in out             # placeholder in bookmarklet

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
