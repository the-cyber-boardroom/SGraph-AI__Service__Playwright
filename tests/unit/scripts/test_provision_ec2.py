# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_ec2.py (v0.1.33 — two-container EC2 stack)
#
# Scope (unit-level, no real AWS):
#   • module surface          — exposes all expected helpers + provision/main.
#   • constants               — t3.large, ports, IAM role/SG/tag names.
#   • preflight_check         — credential failure exits with code 1;
#                               warning when API key default is used;
#                               summary output contains key info.
#   • render_compose_yaml     — both image URIs, key env vars, network, ports.
#   • render_user_data        — docker install, compose plugin, both pulls,
#                               embedded compose YAML, docker compose up.
#   • provision(terminate)    — short-circuits via stubbed terminate helper.
#   • argparse                — --terminate is off by default; new image args.
#
# End-to-end create/terminate is out of scope (local-invoke script, not CI).
# ═══════════════════════════════════════════════════════════════════════════════

import io
import sys
from unittest import TestCase

import pytest

from scripts import provision_ec2
from scripts.provision_ec2 import (DEFAULT_STAGE              ,
                                    EC2__AMI_NAME_AL2023       ,
                                    preflight_check            ,
                                    EC2__INSTANCE_TYPE         ,
                                    EC2__PLAYWRIGHT_PORT       ,
                                    EC2__SIDECAR_ADMIN_PORT    ,
                                    IAM__ECR_READONLY_POLICY_ARN,
                                    IAM__POLICY_ARNS           ,
                                    IAM__ROLE_NAME             ,
                                    IAM__SSM_CORE_POLICY_ARN   ,
                                    SG__NAME                   ,
                                    TAG__NAME                  ,
                                    render_compose_yaml        ,
                                    render_user_data           )


PLAYWRIGHT_URI = '123456789012.dkr.ecr.eu-west-2.amazonaws.com/sgraph_ai_service_playwright:latest'
SIDECAR_URI    = '123456789012.dkr.ecr.eu-west-2.amazonaws.com/agent_mitmproxy:latest'
FAKE_REGISTRY  = '123456789012.dkr.ecr.eu-west-2.amazonaws.com'


def _stub_aws(fn):
    """Stub aws_account_id / aws_region / ecr_registry_host for tests that don't need real creds."""
    orig_account  = provision_ec2.aws_account_id
    orig_region   = provision_ec2.aws_region
    orig_registry = provision_ec2.ecr_registry_host
    provision_ec2.aws_account_id    = lambda: '123456789012'
    provision_ec2.aws_region        = lambda: 'eu-west-2'
    provision_ec2.ecr_registry_host = lambda: FAKE_REGISTRY
    try:
        return fn()
    finally:
        provision_ec2.aws_account_id    = orig_account
        provision_ec2.aws_region        = orig_region
        provision_ec2.ecr_registry_host = orig_registry


class test_preflight_check(TestCase):

    def test__exits_1_when_aws_credentials_missing_exception(self):
        orig = provision_ec2.aws_account_id
        provision_ec2.aws_account_id = lambda: (_ for _ in ()).throw(Exception('Unable to locate credentials'))
        try:
            with pytest.raises(SystemExit) as exc_info:
                preflight_check()
            assert exc_info.value.code == 1
        finally:
            provision_ec2.aws_account_id = orig

    def test__exits_1_when_aws_account_id_returns_none(self):                           # AWS_Config returns None (not exception) when STS call fails silently
        orig = provision_ec2.aws_account_id
        provision_ec2.aws_account_id = lambda: None
        try:
            with pytest.raises(SystemExit) as exc_info:
                preflight_check()
            assert exc_info.value.code == 1
        finally:
            provision_ec2.aws_account_id = orig

    def test__prints_account_region_registry_and_image_uris(self, capsys=None):
        output = io.StringIO()
        orig_stdout = sys.stdout
        sys.stdout  = output
        try:
            _stub_aws(preflight_check)
        finally:
            sys.stdout = orig_stdout
        text = output.getvalue()
        assert '123456789012'   in text
        assert 'eu-west-2'      in text
        assert FAKE_REGISTRY    in text
        assert 'playwright'     in text
        assert 'agent_mitmproxy' in text

    def test__warns_when_api_key_value_not_set(self):
        import os
        orig_key = os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)
        output   = io.StringIO()
        orig_stdout, sys.stdout = sys.stdout, output
        try:
            _stub_aws(preflight_check)
        finally:
            sys.stdout = orig_stdout
            if orig_key is not None:
                os.environ['FAST_API__AUTH__API_KEY__VALUE'] = orig_key
        assert 'FAST_API__AUTH__API_KEY__VALUE' in output.getvalue()

    def test__generates_random_key_when_not_set(self):
        import os
        orig_key = os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)
        try:
            result1 = _stub_aws(preflight_check)
            result2 = _stub_aws(preflight_check)
        finally:
            if orig_key is not None:
                os.environ['FAST_API__AUTH__API_KEY__VALUE'] = orig_key
        assert result1['api_key_value']                                     # non-empty
        assert result1['api_key_value'] != result2['api_key_value']         # different each run

    def test__returns_account_region_registry(self):
        result = _stub_aws(preflight_check)
        assert result['account']      == '123456789012'
        assert result['region']       == 'eu-west-2'
        assert result['registry']     == FAKE_REGISTRY
        assert result['api_key_value']                                      # always returned


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('provision'                  ,
                     'app'                        ,
                     'render_compose_yaml'        ,
                     'render_user_data'           ,
                     'default_playwright_image_uri',
                     'default_sidecar_image_uri'  ,
                     'ensure_instance_profile'    ,
                     'ensure_security_group'      ,
                     'latest_al2023_ami_id'       ,
                     'run_instance'               ,
                     'find_instance_ids'          ,
                     'terminate_instances'        ,
                     'clean_instance_for_ami'     ,
                     'create_ami'                 ,
                     'wait_ami_available'         ,
                     'tag_ami'                    ,
                     'latest_healthy_ami'         ):
            assert hasattr(provision_ec2, attr), f'missing: {attr}'


class test_constants(TestCase):

    def test__stack_pins_match_design(self):
        assert EC2__INSTANCE_TYPE            == 't3.large'                                 # Playwright + sidecar need the headroom
        assert EC2__PLAYWRIGHT_PORT          == 8000
        assert EC2__SIDECAR_ADMIN_PORT       == 8001
        assert EC2__AMI_NAME_AL2023          .startswith('al2023-ami-')
        assert IAM__ECR_READONLY_POLICY_ARN  == 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
        assert IAM__SSM_CORE_POLICY_ARN      == 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        assert IAM__POLICY_ARNS              == (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
        assert IAM__ROLE_NAME                == 'playwright-ec2'                             # No 'sg-*' prefix — AWS reserves it for SG IDs, IAM profiles, and resource names
        assert SG__NAME                      == 'playwright-ec2'
        assert TAG__NAME                     == 'playwright-ec2'
        assert DEFAULT_STAGE                 == 'dev'


class test_render_compose_yaml(TestCase):

    def _render(self, **kwargs):
        defaults = dict(playwright_image_uri = PLAYWRIGHT_URI,
                        sidecar_image_uri    = SIDECAR_URI   ,
                        api_key_name         = 'X-API-Key'   ,
                        api_key_value        = 'test-secret' )
        defaults.update(kwargs)
        return render_compose_yaml(**defaults)

    def test__contains_both_image_uris(self):
        yaml = self._render()
        assert PLAYWRIGHT_URI in yaml
        assert SIDECAR_URI    in yaml

    def test__playwright_on_correct_port(self):
        yaml = self._render()
        assert f'"{EC2__PLAYWRIGHT_PORT}:{EC2__PLAYWRIGHT_PORT}"' in yaml

    def test__sidecar_admin_mapped_to_8001(self):
        yaml = self._render()
        assert f'"{EC2__SIDECAR_ADMIN_PORT}:8000"' in yaml

    def test__playwright_routes_through_sidecar(self):
        yaml = self._render()
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL:' in yaml
        assert 'http://agent-mitmproxy:8080'       in yaml
        assert 'SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS:' in yaml
        assert "'true'"                              in yaml

    def test__api_key_in_both_services(self):
        yaml = self._render(api_key_name='X-API-Key', api_key_value='test-secret')
        assert yaml.count("'X-API-Key'")    == 2                                           # Playwright + sidecar both get the key
        assert yaml.count("'test-secret'")  == 3                                           # Playwright, sidecar FAST_API, sidecar WEB_PASSWORD

    def test__mitmweb_web_password_set(self):
        yaml = self._render(api_key_value='test-secret')
        assert 'AGENT_MITMPROXY__WEB_PASSWORD' in yaml
        assert yaml.count("'test-secret'") == 3                                            # same value used for mitmweb UI password

    def test__upstream_vars_included(self):
        yaml = self._render(upstream_url='http://corp:3128', upstream_user='u', upstream_pass='p')
        assert 'http://corp:3128' in yaml
        assert "'u'"              in yaml
        assert "'p'"              in yaml

    def test__sg_net_network_defined(self):
        yaml = self._render()
        assert 'sg-net'        in yaml
        assert 'driver: bridge' in yaml

    def test__depends_on_sidecar(self):
        yaml = self._render()
        assert 'depends_on'      in yaml
        assert 'agent-mitmproxy' in yaml

    def test__restart_always(self):
        yaml = self._render()
        assert yaml.count('restart: always') == 2                                          # Both services


class test_render_user_data(TestCase):

    def _render(self, **kwargs):
        compose           = render_compose_yaml(playwright_image_uri = PLAYWRIGHT_URI,
                                                sidecar_image_uri    = SIDECAR_URI   ,
                                                api_key_name         = 'X-API-Key'   ,
                                                api_key_value        = 'secret'      )
        orig_region   = provision_ec2.aws_region
        orig_registry = provision_ec2.ecr_registry_host
        try:
            provision_ec2.aws_region        = lambda: 'eu-west-2'
            provision_ec2.ecr_registry_host = lambda: '123456789012.dkr.ecr.eu-west-2.amazonaws.com'
            return render_user_data(playwright_image_uri = PLAYWRIGHT_URI ,
                                    sidecar_image_uri    = SIDECAR_URI    ,
                                    compose_content      = compose        )
        finally:
            provision_ec2.aws_region        = orig_region
            provision_ec2.ecr_registry_host = orig_registry

    def test__starts_with_shebang(self):
        assert self._render().startswith('#!/bin/bash')

    def test__installs_docker_and_compose_plugin(self):
        ud = self._render()
        assert 'dnf install -y docker'              in ud
        assert 'docker-compose-linux-x86_64'        in ud   # compose v2 plugin binary
        assert '/usr/local/lib/docker/cli-plugins'  in ud

    def test__ecr_login_uses_region(self):
        ud = self._render()
        assert 'aws ecr get-login-password --region eu-west-2' in ud
        assert 'docker login --username AWS --password-stdin'  in ud
        assert 'set +x'                                        in ud   # token never logged
        assert 'docker logout'                                 in ud   # credential wiped after pull
        assert 'rm -f /root/.docker/config.json'              in ud

    def test__pulls_both_images(self):
        ud = self._render()
        assert f'docker pull {PLAYWRIGHT_URI}' in ud
        assert f'docker pull {SIDECAR_URI}'    in ud

    def test__writes_compose_file_and_runs_up(self):
        ud = self._render()
        assert '/opt/sg-playwright/docker-compose.yml' in ud
        assert 'docker compose'                        in ud
        assert 'up -d'                                 in ud

    def test__compose_content_embedded_verbatim(self):
        ud = self._render()
        assert PLAYWRIGHT_URI in ud
        assert SIDECAR_URI    in ud
        assert 'sg-net'       in ud


class test_provision_terminate(TestCase):

    def test__terminate_calls_helper_and_returns_action(self):
        calls = []
        original = provision_ec2.terminate_instances
        try:
            provision_ec2.terminate_instances = lambda ec2: calls.append(ec2) or ['i-abc123']
            result = provision_ec2.provision(terminate=True)
        finally:
            provision_ec2.terminate_instances = original

        assert len(calls) == 1
        assert result     == {'action': 'terminate', 'instance_ids': ['i-abc123']}


class test_cli_surface(TestCase):

    def test__app_has_expected_commands(self):
        from typer.testing import CliRunner
        result = CliRunner().invoke(provision_ec2.app, ['--help'])
        assert result.exit_code == 0
        for cmd in ('create', 'list', 'delete', 'connect', 'exec', 'logs', 'forward', 'wait',
                    'health', 'open', 'smoke', 'clean', 'bake-ami', 'wait-ami', 'tag-ami'):
            assert cmd in result.output, f'command {cmd!r} missing from --help'

    def test__create_help_shows_expected_options(self):
        from typer.testing import CliRunner
        result = CliRunner().invoke(provision_ec2.app, ['create', '--help'])
        assert result.exit_code == 0
        for opt in ('--stage', '--name', '--playwright-image-uri', '--sidecar-image-uri', '--wait', '--timeout'):
            assert opt in result.output, f'option {opt!r} missing from create --help'
