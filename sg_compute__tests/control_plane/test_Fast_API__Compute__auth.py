# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Fast_API__Compute auth (negative-path)
# Verifies that API-key enforcement is wired correctly:
#   • every protected route rejects requests missing X-API-Key with 401
#   • health routes bypass auth (load-balancer / Lambda probes)
#   • a valid key grants access
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                 import TestCase

from fastapi.testclient                                                       import TestClient

from sg_compute.control_plane.Fast_API__Compute                              import Fast_API__Compute

TEST_API_KEY = 'test-api-key-auth-1234567890'                                 # ≥ 16 chars; not a real key


class test_Fast_API__Compute__auth(TestCase):

    def setUp(self):
        os.environ['FAST_API__AUTH__API_KEY__VALUE'] = TEST_API_KEY
        os.environ['FAST_API__AUTH__API_KEY__NAME']  = 'X-API-Key'
        self.fast_api      = Fast_API__Compute().setup()
        self.client_no_key = TestClient(self.fast_api.app(), raise_server_exceptions=False)
        self.client_ok     = TestClient(self.fast_api.app(), headers={'X-API-Key': TEST_API_KEY})

    def tearDown(self):
        os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)
        os.environ.pop('FAST_API__AUTH__API_KEY__NAME' , None)

    # ── health routes bypass auth ────────────────────────────────────────────

    def test_health_ping_no_key_is_200(self):                                  # load-balancer probes must not need creds
        r = self.client_no_key.get('/api/health')
        assert r.status_code == 200

    def test_health_ready_no_key_is_200(self):
        r = self.client_no_key.get('/api/health/ready')
        assert r.status_code == 200

    # ── protected routes reject missing key ──────────────────────────────────

    def test_specs_no_key_is_401(self):
        r = self.client_no_key.get('/api/specs')
        assert r.status_code == 401

    def test_nodes_no_key_is_401(self):
        r = self.client_no_key.get('/api/nodes')
        assert r.status_code == 401

    def test_stacks_no_key_is_401(self):
        r = self.client_no_key.get('/api/stacks')
        assert r.status_code == 401

    def test_spec_detail_no_key_is_401(self):
        r = self.client_no_key.get('/api/specs/docker')
        assert r.status_code == 401

    # ── valid key grants access ──────────────────────────────────────────────

    def test_specs_with_key_is_200(self):
        r = self.client_ok.get('/api/specs')
        assert r.status_code == 200

    def test_spec_detail_with_key_is_200(self):
        r = self.client_ok.get('/api/specs/docker')
        assert r.status_code == 200

    def test_stacks_with_key_is_200(self):
        r = self.client_ok.get('/api/stacks')
        assert r.status_code == 200

    # ── wrong key is rejected ────────────────────────────────────────────────

    def test_specs_wrong_key_is_401(self):
        client = TestClient(self.fast_api.app(), headers={'X-API-Key': 'wrong-key-000000000'})
        r = client.get('/api/specs')
        assert r.status_code == 401

    # ── boot assertion fires when key env var is absent ──────────────────────

    def test_boot_assertion_no_env_var(self):
        os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)
        try:
            Fast_API__Compute().setup()
            raise AssertionError('Expected AssertionError not raised')
        except AssertionError as e:
            assert 'refuses to start' in str(e) or 'unset' in str(e)
        finally:
            os.environ['FAST_API__AUTH__API_KEY__VALUE'] = TEST_API_KEY        # restore for tearDown

    def test_boot_assertion_key_too_short(self):
        os.environ['FAST_API__AUTH__API_KEY__VALUE'] = 'short'
        try:
            Fast_API__Compute().setup()
            raise AssertionError('Expected AssertionError not raised')
        except AssertionError as e:
            assert 'refuses to start' in str(e) or 'shorter than 16' in str(e)
        finally:
            os.environ['FAST_API__AUTH__API_KEY__VALUE'] = TEST_API_KEY        # restore for tearDown
