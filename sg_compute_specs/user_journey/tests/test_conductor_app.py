# ═══════════════════════════════════════════════════════════════════════════════
# Tests — conductor_app (the conductor container entry, minus uvicorn)
# `app` builds + serves the suite routes; configure_runtime() stays in-memory when no
# Docker daemon is reachable (the common test/CI case). No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from fastapi.testclient import TestClient

from sg_compute_specs.user_journey.core.conductor.api                       import conductor_app
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__InMemory import Worker__Runtime__InMemory
from sg_compute_specs.user_journey.core.conductor.Worker__Runtime__Docker   import docker_available
from sg_compute_specs.user_journey.core.conductor.api.routes.Routes__Suites import SUITE_SERVICE


def test__app_serves_suite_routes():
    os.environ['FAST_API__AUTH__API_KEY__NAME' ] = 'X-API-Key'
    os.environ['FAST_API__AUTH__API_KEY__VALUE'] = 'k'
    try:
        client   = TestClient(conductor_app.app)
        response = client.post('/suites',
                               json={'suite_id': 'nightly',
                                     'entries' : [{'journey_id': 'checkout', 'count': 1, 'concurrency': 1}],
                                     'tags'    : []},
                               headers={'X-API-Key': 'k'})
        assert response.status_code == 200
        assert response.json()['state'] == 'running'
    finally:
        os.environ.pop('FAST_API__AUTH__API_KEY__NAME' , None)
        os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)


def test__configure_runtime_matches_docker_availability():
    saved = SUITE_SERVICE.runtime
    try:
        swapped = conductor_app.configure_runtime()
        assert swapped == docker_available()                                        # honest: swaps iff a daemon is reachable
        if not swapped:
            assert isinstance(SUITE_SERVICE.runtime, Worker__Runtime__InMemory)
    finally:
        SUITE_SERVICE.runtime = saved
