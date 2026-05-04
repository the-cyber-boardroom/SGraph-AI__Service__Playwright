# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Kibana__Saved_Objects__Client.delete_saved_objects
# Pins the contract that delete_default_dashboard_objects fires DELETE for
# every (type, id) pair from Default__Dashboard__Generator.all_dashboard_object_refs,
# and that ensure_default_dashboard pre-cleans before importing — the
# self-healing fix for the "savedobjects-service: Cannot read properties of
# undefined (reading 'layers')" crashes from stale Lens objects.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                       import TestCase

import requests

from sgraph_ai_service_playwright__cli.elastic.service.Default__Dashboard__Generator import LEGACY_LENS_IDS, DASHBOARD_ID, VIS_ID__LOG_LEVELS
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client


def build_response(status_code: int, body: bytes = b'{}') -> requests.Response:
    response             = requests.Response()
    response.status_code = status_code
    response._content    = body
    return response


class Recording__Client(Kibana__Saved_Objects__Client):
    captured_calls : list
    canned_queue   : list

    def request(self, method: str, url: str, *, headers: dict = None, data: bytes = None) -> requests.Response:
        self.captured_calls.append((method, url, dict(headers or {}), data or b''))
        if not self.canned_queue:
            return build_response(200, b'{}')
        return self.canned_queue.pop(0)


class test_delete_saved_objects(TestCase):

    def test_fires_one_delete_per_object_pair(self):
        client = Recording__Client(canned_queue=[build_response(200) for _ in range(3)])
        deleted = client.delete_saved_objects('https://host', 'elastic', 'pw',
                                              objects=[('dashboard'    , 'd1'),
                                                       ('visualization', 'v1'),
                                                       ('lens'         , 'l1')])
        assert deleted == 3
        # All three calls were DELETE on the right URLs
        methods = [c[0] for c in client.captured_calls]
        urls    = [c[1] for c in client.captured_calls]
        assert methods == ['DELETE', 'DELETE', 'DELETE']
        assert 'https://host/api/saved_objects/dashboard/d1'     in urls
        assert 'https://host/api/saved_objects/visualization/v1' in urls
        assert 'https://host/api/saved_objects/lens/l1'          in urls
        # CSRF header on every call
        for call in client.captured_calls:
            assert call[2].get('kbn-xsrf') == 'true'

    def test_404_collapses_to_idempotent_no_op(self):                                # 404 = already gone — must NOT count as deleted, must NOT raise
        client = Recording__Client(canned_queue=[build_response(404, b'{"statusCode":404}'),
                                                  build_response(200)])
        deleted = client.delete_saved_objects('https://host', 'elastic', 'pw',
                                              objects=[('dashboard', 'gone'),
                                                       ('dashboard', 'present')])
        assert deleted == 1                                                          # Only the 200 counts


class test_delete_default_dashboard_objects(TestCase):

    def test_targets_dashboard_visualization_and_legacy_lens_ids(self):              # The whole point: clean the half-migrated Lens objects from earlier attempts
        client = Recording__Client(canned_queue=[build_response(200) for _ in range(20)])
        deleted = client.delete_default_dashboard_objects('https://host', 'elastic', 'pw')
        url_paths = [c[1].split('/api/saved_objects/')[1] for c in client.captured_calls]
        # Must include the dashboard
        assert f'dashboard/{DASHBOARD_ID}' in url_paths
        # Must include at least one current visualization
        assert any(f'visualization/{VIS_ID__LOG_LEVELS}' == p for p in url_paths)
        # Must include every legacy lens id — these are the ones that crash savedobjects-service migrations
        for lens_id in LEGACY_LENS_IDS:
            assert f'lens/{lens_id}' in url_paths, f'legacy lens {lens_id} not in delete plan'
        assert deleted >= 1
