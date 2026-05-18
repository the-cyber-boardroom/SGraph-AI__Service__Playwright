# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — tests for Section__Sidecar
#
# Sidecar is now pulled directly from Docker Hub (diniscruz/sg-host-control).
# No ECR login, no /root/.docker/config.json cleanup. The include-gate is the
# SSM key path: without it the sidecar can't fetch an API key, so we skip it.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.platforms.ec2.user_data.Section__Sidecar                            import (Section__Sidecar    ,
                                                                                             CONTAINER_NAME      ,
                                                                                             DEFAULT_PORT        ,
                                                                                             HOST_CONTROL_IMAGE  ,
                                                                                             TEMPLATE            )


SAMPLE_REGISTRY = '123456789.dkr.ecr.eu-west-2.amazonaws.com'                       # legacy/unused — still accepted for caller compatibility
SAMPLE_KEY_NAME = 'X-API-Key'
SAMPLE_SSM_PATH = '/sg-compute/nodes/test-node-001/sidecar-api-key'


class test_Section__Sidecar(TestCase):

    def setUp(self):
        self.sidecar = Section__Sidecar()

    def test_constants(self):
        assert HOST_CONTROL_IMAGE == 'diniscruz/sg-host-control'                    # Docker Hub — dedicated host-control image
        assert CONTAINER_NAME     == 'sg-sidecar'
        assert DEFAULT_PORT       == 19009

    def test_render_returns_empty_when_ssm_path_is_empty(self):                     # include-gate is now api_key_ssm_path
        assert self.sidecar.render() == ''
        assert self.sidecar.render(api_key_ssm_path='') == ''
        assert self.sidecar.render(registry=SAMPLE_REGISTRY) == ''                  # registry alone is not enough

    def test_render_returns_string_when_ssm_path_set(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_uses_docker_hub_image(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert HOST_CONTROL_IMAGE in result
        assert 'diniscruz/sg-host-control:latest' in result

    def test_render_does_not_prefix_image_with_registry(self):                      # Docker Hub image — no ECR registry prefix
        result = self.sidecar.render(registry=SAMPLE_REGISTRY, api_key_ssm_path=SAMPLE_SSM_PATH)
        assert f'{SAMPLE_REGISTRY}/diniscruz' not in result
        assert f'{SAMPLE_REGISTRY}/sg-host-control' not in result

    def test_render_does_no_ecr_login(self):                                        # public Docker Hub image — no login required
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert 'ecr get-login-password' not in result
        assert 'docker login'           not in result

    def test_render_does_not_clean_docker_config(self):                             # nothing to clean — no docker login happened
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert '/root/.docker/config.json' not in result

    def test_render_contains_container_name(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert CONTAINER_NAME in result

    def test_render_contains_default_port(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert str(DEFAULT_PORT) in result

    def test_render_contains_api_key_name(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH, api_key_name=SAMPLE_KEY_NAME)
        assert SAMPLE_KEY_NAME in result

    def test_render_contains_ssm_path(self):                                        # key comes from SSM, not plaintext
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert SAMPLE_SSM_PATH in result

    def test_render_fetches_key_from_ssm(self):                                     # user-data must call aws ssm get-parameter, not embed key
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert 'ssm get-parameter' in result
        assert '--with-decryption' in result

    def test_render_has_no_privileged_flag(self):                                   # T1.2 — Docker socket only, never --privileged
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert '--privileged' not in result

    def test_render_mounts_docker_socket(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert '/var/run/docker.sock' in result

    def test_render_uses_custom_port(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH, port=9999)
        assert '9999' in result
        assert str(DEFAULT_PORT) not in result

    def test_render_uses_image_tag_latest_by_default(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH)
        assert ':latest' in result

    def test_render_uses_custom_image_tag(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH, image_tag='v1.2.3')
        assert ':v1.2.3' in result

    def test_template_has_no_unresolved_placeholders(self):
        result = self.sidecar.render(registry         = SAMPLE_REGISTRY ,
                                     api_key_name     = SAMPLE_KEY_NAME ,
                                     api_key_ssm_path = SAMPLE_SSM_PATH )
        assert '{' not in result or '${' in result                                  # bash vars only, no Python {placeholders}

    def test_enable_shell_false__no_unrestricted_env(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH, enable_shell=False)
        assert 'SG_SHELL_UNRESTRICTED' not in result

    def test_enable_shell_true__injects_env_var(self):
        result = self.sidecar.render(api_key_ssm_path=SAMPLE_SSM_PATH, enable_shell=True)
        assert 'SG_SHELL_UNRESTRICTED=1' in result

    def test_enable_shell_true__no_unresolved_placeholders(self):
        result = self.sidecar.render(api_key_ssm_path = SAMPLE_SSM_PATH ,
                                     api_key_name     = SAMPLE_KEY_NAME ,
                                     enable_shell     = True            )
        assert '{' not in result or '${' in result
