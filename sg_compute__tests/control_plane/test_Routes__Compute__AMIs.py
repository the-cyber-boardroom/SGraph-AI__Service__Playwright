# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Routes__Compute__AMIs + AMI__Lister
# In-memory composition: fake AMI__Lister; zero AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from fastapi.testclient import TestClient
from osbot_fast_api.api.Fast_API import Fast_API

from sg_compute.control_plane.routes.Routes__Compute__AMIs     import Routes__Compute__AMIs
from sg_compute.core.ami.schemas.Schema__AMI__Info              import Schema__AMI__Info
from sg_compute.core.ami.schemas.Schema__AMI__List__Response    import Schema__AMI__List__Response
from sg_compute.core.ami.service.AMI__Lister                    import AMI__Lister


# ── fake lister — no AWS calls ───────────────────────────────────────────────

class Fake__AMI__Lister(AMI__Lister):

    def list_amis(self, spec_id: str) -> Schema__AMI__List__Response:
        resp = Schema__AMI__List__Response(spec_id=spec_id)
        if spec_id == 'docker':
            ami = Schema__AMI__Info(ami_id     = 'ami-0a1b2c3d4e5f67890',
                                    name       = 'docker-base-20260505'  ,
                                    created_at = '2026-05-05T10:00:00Z'  ,
                                    state      = 'available'             ,
                                    size_gb    = 8                       )
            resp.amis.append(ami)
        return resp


def _client() -> TestClient:
    fast_api = Fast_API()
    fast_api.add_routes(Routes__Compute__AMIs, prefix='/api/amis', lister=Fake__AMI__Lister())
    return TestClient(fast_api.app())


# ── route tests ──────────────────────────────────────────────────────────────

class test_Routes__Compute__AMIs(TestCase):

    def test_list_amis__known_spec(self):
        r    = _client().get('/api/amis?spec_id=docker')
        assert r.status_code == 200
        data = r.json()
        assert data['spec_id']         == 'docker'
        assert len(data['amis'])       == 1
        assert data['amis'][0]['ami_id']     == 'ami-0a1b2c3d4e5f67890'
        assert data['amis'][0]['name']       == 'docker-base-20260505'
        assert data['amis'][0]['size_gb']    == 8
        assert data['amis'][0]['state']      == 'available'

    def test_list_amis__unknown_spec_returns_empty(self):
        r    = _client().get('/api/amis?spec_id=nonexistent')
        assert r.status_code == 200
        data = r.json()
        assert data['amis'] == []

    def test_list_amis__no_spec_returns_empty(self):
        r    = _client().get('/api/amis')
        assert r.status_code == 200
        data = r.json()
        assert data['amis'] == []


# ── AMI__Lister unit tests ────────────────────────────────────────────────────

class test_AMI__Lister(TestCase):

    def test_list_amis__no_credentials_returns_empty(self):
        lister = AMI__Lister(region='eu-west-2')
        result = lister.list_amis('docker')
        assert isinstance(result, Schema__AMI__List__Response)
        assert result.amis == []                                               # boto3 fails → empty list gracefully

    def test_map_image(self):
        raw = {'ImageId'      : 'ami-0a1b2c3d4e5f67890',
               'Name'         : 'docker-base-20260505'  ,
               'CreationDate' : '2026-05-05T10:00:00Z'  ,
               'State'        : 'available'             ,
               'BlockDeviceMappings': [{'Ebs': {'VolumeSize': 8}}]}
        ami = AMI__Lister._map_image(raw)
        assert isinstance(ami, Schema__AMI__Info)
        assert str(ami.ami_id) == 'ami-0a1b2c3d4e5f67890'
        assert ami.name        == 'docker-base-20260505'
        assert ami.size_gb     == 8
        assert ami.state       == 'available'
