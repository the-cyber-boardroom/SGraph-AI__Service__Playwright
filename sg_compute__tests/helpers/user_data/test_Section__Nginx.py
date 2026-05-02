# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Nginx
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.helpers.user_data.Section__Nginx import Section__Nginx


class test_Section__Nginx(TestCase):

    def test_render__sse_safe_config(self):
        out = Section__Nginx().render(app_port=7456)
        assert 'proxy_buffering    off' in out
        assert 'gzip               off' in out
        assert 'proxy_read_timeout 3600s' in out

    def test_render__correct_port(self):
        out = Section__Nginx().render(app_port=7456)
        assert 'localhost:7456' in out

    def test_render__ssl_cert(self):
        out = Section__Nginx().render()
        assert 'openssl req' in out
        assert '443 ssl' in out

    def test_render__docker_run(self):
        out = Section__Nginx().render()
        assert 'docker run' in out
        assert 'nginx:alpine' in out
