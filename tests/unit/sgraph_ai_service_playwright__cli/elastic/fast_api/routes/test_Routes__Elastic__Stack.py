# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Elastic__Stack: list and info endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.fast_api.routes.fake_elastic_service import (
    _Fake_Elastic__Service, _client, STACK_NAME, INSTANCE_ID
)


class test_list_and_info(TestCase):

    def test_list__non_empty(self):
        resp = _client(_Fake_Elastic__Service(hit=True)).get('/elastic/stacks')
        assert resp.status_code == 200
        body = resp.json()
        assert len(body['stacks'])                    == 1
        assert body['stacks'][0]['stack_name']        == STACK_NAME
        assert body['stacks'][0]['instance_id']       == INSTANCE_ID

    def test_list__empty(self):
        resp = _client(_Fake_Elastic__Service(hit=False)).get('/elastic/stacks')
        assert resp.status_code      == 200
        assert resp.json()['stacks'] == []

    def test_list__region_passed_through(self):
        resp = _client(_Fake_Elastic__Service()).get('/elastic/stacks?region=us-east-1')
        assert resp.status_code     == 200
        assert resp.json()['region'] == 'us-east-1'

    def test_info__hit(self):
        resp = _client(_Fake_Elastic__Service(hit=True)).get(f'/elastic/stack/{STACK_NAME}')
        assert resp.status_code     == 200
        body = resp.json()
        assert body['instance_id']  == INSTANCE_ID
        assert body['state']        == 'running'

    def test_info__miss_returns_404(self):
        resp = _client(_Fake_Elastic__Service(hit=False)).get('/elastic/stack/no-such-thing')
        assert resp.status_code == 404
        assert 'no elastic stack' in resp.json()['detail']
