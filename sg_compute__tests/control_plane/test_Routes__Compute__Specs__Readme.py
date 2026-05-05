# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Specs (readme endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Specs                  import Routes__Compute__Specs
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader


class test_Routes__Compute__Specs__Readme(TestCase):

    def setUp(self):
        self.registry = Spec__Loader().load_all()
        fast_api      = Fast_API()
        fast_api.add_routes(Routes__Compute__Specs, prefix='/api/specs', registry=self.registry)
        self.client   = TestClient(fast_api.app())

    def test_readme_returns_200_for_spec_with_readme(self):
        r = self.client.get('/api/specs/firefox/readme')
        assert r.status_code == 200
        assert 'text/markdown' in r.headers['content-type']
        assert len(r.text) > 0

    def test_readme_content_is_markdown(self):
        r = self.client.get('/api/specs/firefox/readme')
        assert r.status_code == 200
        assert '# Firefox' in r.text                                           # heading from the README

    def test_readme_404_for_spec_without_readme(self):
        r = self.client.get('/api/specs/docker/readme')
        assert r.status_code == 404
        assert 'no README' in r.json()['detail']

    def test_readme_404_for_unknown_spec(self):
        r = self.client.get('/api/specs/no_such_spec/readme')
        assert r.status_code == 404
        assert 'not found' in r.json()['detail']

    def test_readme_root_override(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            spec_dir = os.path.join(tmp, 'sg_compute_specs', 'docker')
            os.makedirs(spec_dir)
            with open(os.path.join(spec_dir, 'README.md'), 'w') as f:
                f.write('# Docker Test README\n\nTest content.')
            fast_api = Fast_API()
            fast_api.add_routes(Routes__Compute__Specs, prefix='/api/specs',
                                registry=self.registry, readme_root_override=tmp)
            client = TestClient(fast_api.app())
            r      = client.get('/api/specs/docker/readme')
            assert r.status_code == 200
            assert '# Docker Test README' in r.text
