# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__Specs
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient
from osbot_fast_api.api.Fast_API                                              import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__Specs                  import Routes__Compute__Specs
from sg_compute.core.spec.Spec__Loader                                       import Spec__Loader


class test_Routes__Compute__Specs(TestCase):

    def setUp(self):
        self.registry = Spec__Loader().load_all()
        fast_api      = Fast_API()
        fast_api.add_routes(Routes__Compute__Specs, prefix='/api/specs', registry=self.registry)
        self.client   = TestClient(fast_api.app())

    def test_catalogue_returns_all_specs(self):
        r = self.client.get('/api/specs')
        assert r.status_code == 200
        data = r.json()
        assert 'specs' in data
        assert len(data['specs']) >= 4

    def test_catalogue_spec_ids(self):
        r       = self.client.get('/api/specs')
        ids     = {s['spec_id'] for s in r.json()['specs']}
        assert 'docker'      in ids
        assert 'ollama'      in ids
        assert 'open_design' in ids
        assert 'podman'      in ids

    def test_spec_info_returns_entry(self):
        r = self.client.get('/api/specs/docker')
        assert r.status_code == 200
        data = r.json()
        assert data['spec_id']      == 'docker'
        assert data['display_name'] != ''

    def test_spec_info_missing_returns_404(self):
        r = self.client.get('/api/specs/no_such_spec')
        assert r.status_code == 404
        assert 'not found' in r.json()['detail']

    def test_catalogue_entries_have_required_fields(self):
        r   = self.client.get('/api/specs')
        for entry in r.json()['specs']:
            assert 'spec_id'      in entry
            assert 'display_name' in entry
            assert 'version'      in entry
