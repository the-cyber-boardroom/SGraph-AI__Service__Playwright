# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Elastic__Stack: create / delete / health endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.elastic.fast_api.routes.fake_elastic_service import (
    _Fake_Elastic__Service, _client, STACK_NAME, INSTANCE_ID
)


class test_create(TestCase):

    def test_create__minimal_body(self):
        svc  = _Fake_Elastic__Service()
        resp = _client(svc).post('/elastic/stack', json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body['instance_id']      == INSTANCE_ID
        assert body['elastic_password']                   # Returned once
        assert body['state']            == 'pending'
        assert svc.last_create_req is not None

    def test_create__pinned_stack_name(self):
        svc  = _Fake_Elastic__Service()
        resp = _client(svc).post('/elastic/stack', json={'stack_name': 'elastic-prod'})
        assert resp.status_code == 200
        assert svc.last_create_req is not None


class test_delete(TestCase):

    def test_delete__hit(self):
        resp = _client(_Fake_Elastic__Service(hit=True)).delete(f'/elastic/stack/{STACK_NAME}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['target']                  == INSTANCE_ID
        assert body['terminated_instance_ids'] == [INSTANCE_ID]

    def test_delete__miss_returns_404(self):
        resp = _client(_Fake_Elastic__Service(hit=False)).delete('/elastic/stack/no-such-thing')
        assert resp.status_code == 404
        assert 'no elastic stack' in resp.json()['detail']


class test_health(TestCase):

    def test_health__returns_ok(self):
        resp = _client(_Fake_Elastic__Service()).get(f'/elastic/stack/{STACK_NAME}/health')
        assert resp.status_code == 200
        body = resp.json()
        assert body['all_ok']         is True
        assert body['stack_name']     == STACK_NAME
        assert len(body['checks'])    == 1
        assert body['checks'][0]['status'] == 'ok'
