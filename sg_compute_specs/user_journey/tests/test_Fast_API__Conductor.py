# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Conductor (suite API over the in-memory runtime; TestClient)
# Closes the Conductor__Client <-> conductor loop: start -> get -> report -> stop.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from sg_compute_specs.user_journey.core.conductor.api.Fast_API__Conductor            import Fast_API__Conductor
from sg_compute_specs.user_journey.core.conductor.api.routes.Routes__Suites          import (SUITE_SERVICE,
                                                                                             ROUTES_PATHS__SUITES,
                                                                                             TAG__ROUTES_SUITES)

API_KEY_ENV_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
API_KEY_ENV_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'
API_KEY_HEADER    = 'X-API-Key'
API_KEY_VALUE     = 'test-key-conductor'


def _definition_body():
    return {'suite_id': 'nightly',
            'entries' : [{'journey_id': 'checkout', 'count': 3, 'concurrency': 2}],
            'tags'    : []}


class test_constants(TestCase):

    def test__tag_and_paths(self):
        assert TAG__ROUTES_SUITES == 'suites'
        assert '/suites'                       in ROUTES_PATHS__SUITES
        assert '/suites/{suite_run_id}'        in ROUTES_PATHS__SUITES


class test_Fast_API__Conductor(TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ[API_KEY_ENV_NAME ] = API_KEY_HEADER
        os.environ[API_KEY_ENV_VALUE] = API_KEY_VALUE
        cls.client = TestClient(Fast_API__Conductor().setup().app())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop(API_KEY_ENV_NAME , None)
        os.environ.pop(API_KEY_ENV_VALUE, None)

    def setUp(self):
        SUITE_SERVICE.runs.clear()

    def _auth(self):
        return {API_KEY_HEADER: API_KEY_VALUE}

    def test__start_then_get_then_report_then_stop(self):
        started = self.client.post('/suites', json=_definition_body(), headers=self._auth())
        assert started.status_code == 200
        body = started.json()
        assert body['state']             == 'running'
        assert len(body['workers'])      == 3
        assert int(body['counts']['running']) == 3
        run_id    = body['suite_run_id']
        worker_id = body['workers'][0]['worker_id']

        fetched = self.client.get(f'/suites/{run_id}', headers=self._auth())
        assert fetched.status_code        == 200
        assert len(fetched.json()['workers']) == 3

        reported = self.client.post(f'/suites/{run_id}/report/{worker_id}',
                                    json={'state': 'passed'}, headers=self._auth())
        assert reported.status_code               == 200
        assert int(reported.json()['counts']['passed']) == 1

        stopped = self.client.post(f'/suites/{run_id}/stop', headers=self._auth())
        assert stopped.status_code        == 200
        assert stopped.json()['state']    == 'stopped'

    def test__scale_grows_worker_count(self):
        started = self.client.post('/suites', json=_definition_body(), headers=self._auth())   # count=3
        run_id  = started.json()['suite_run_id']
        scaled  = self.client.post(f'/suites/{run_id}/scale', json={'count': 5, 'concurrency': 5}, headers=self._auth())
        assert scaled.status_code              == 200
        assert len(scaled.json()['workers'])   == 5

    def test__get_unknown_is_404(self):
        response = self.client.get('/suites/does-not-exist', headers=self._auth())
        assert response.status_code == 404

    def test__report_bad_state_is_422(self):
        started   = self.client.post('/suites', json=_definition_body(), headers=self._auth())
        run_id    = started.json()['suite_run_id']
        worker_id = started.json()['workers'][0]['worker_id']
        response  = self.client.post(f'/suites/{run_id}/report/{worker_id}',
                                     json={'state': 'bogus'}, headers=self._auth())
        assert response.status_code == 422

    def test__requires_api_key(self):
        response = self.client.post('/suites', json=_definition_body())               # no auth header
        assert response.status_code == 401
