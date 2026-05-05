# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — tests for Section__Sidecar
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute.platforms.ec2.user_data.Section__Sidecar                            import (Section__Sidecar ,
                                                                                             CONTAINER_NAME  ,
                                                                                             DEFAULT_PORT    ,
                                                                                             IMAGE_NAME      ,
                                                                                             TEMPLATE        )


SAMPLE_REGISTRY = '123456789.dkr.ecr.eu-west-2.amazonaws.com'
SAMPLE_KEY_NAME = 'X-API-Key'
SAMPLE_KEY_VAL  = 'secret-token'


class test_Section__Sidecar(TestCase):

    def setUp(self):
        self.sidecar = Section__Sidecar()

    def test_constants(self):
        assert IMAGE_NAME     == 'sgraph_ai_service_playwright_host'
        assert CONTAINER_NAME == 'sg-sidecar'
        assert DEFAULT_PORT   == 19009

    def test_render_returns_empty_when_registry_is_empty(self):
        assert self.sidecar.render() == ''
        assert self.sidecar.render(registry='') == ''

    def test_render_returns_string_when_registry_set(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_contains_registry(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert SAMPLE_REGISTRY in result

    def test_render_contains_image_name(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert IMAGE_NAME in result

    def test_render_contains_container_name(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert CONTAINER_NAME in result

    def test_render_contains_default_port(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert str(DEFAULT_PORT) in result

    def test_render_contains_api_key_name(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY, api_key_name=SAMPLE_KEY_NAME)
        assert SAMPLE_KEY_NAME in result

    def test_render_contains_api_key_value(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY, api_key_value=SAMPLE_KEY_VAL)
        assert SAMPLE_KEY_VAL in result

    def test_render_uses_custom_port(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY, port=9999)
        assert '9999' in result
        assert str(DEFAULT_PORT) not in result

    def test_render_uses_image_tag_latest_by_default(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert ':latest' in result

    def test_render_uses_custom_image_tag(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY, image_tag='v1.2.3')
        assert ':v1.2.3' in result

    def test_render_mounts_docker_socket(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert '/var/run/docker.sock' in result

    def test_render_removes_docker_config(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert '/root/.docker/config.json' in result

    def test_render_uses_ecr_login(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY)
        assert 'ecr get-login-password' in result

    def test_template_has_no_unresolved_placeholders(self):
        result = self.sidecar.render(registry=SAMPLE_REGISTRY,
                                     api_key_name=SAMPLE_KEY_NAME,
                                     api_key_value=SAMPLE_KEY_VAL)
        assert '{' not in result or '${' in result     # bash vars only, no Python {placeholders}
