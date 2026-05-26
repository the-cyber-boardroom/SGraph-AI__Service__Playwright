# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.core.addons.run_capture_addon
#
# Duck-typed against a fake Flow (SimpleNamespace) — mitmproxy need not be installed.
# ═══════════════════════════════════════════════════════════════════════════════

from types                                                                           import SimpleNamespace
from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.core.addons.run_capture_addon                        import (Run_Capture           ,
                                                                                             Run__Capture__Buffer  ,
                                                                                             RUN_CAPTURE           ,
                                                                                             HEADER__RUN_ID        ,
                                                                                             MAX_RUNS              ,
                                                                                             MAX_RECORDS_PER_RUN   ,
                                                                                             addons                )


def _flow(run_id=None, url='https://shop.test/pay', method='POST', status=200):
    headers = {HEADER__RUN_ID: run_id} if run_id is not None else {}
    return SimpleNamespace(request  = SimpleNamespace(url=url, method=method, headers=headers, timestamp_start=123.0),
                           response = SimpleNamespace(status_code=status, headers={'content-type': 'text/html'}))


class test_Run_Capture(TestCase):

    def setUp(self):
        RUN_CAPTURE.clear()

    def test__captures_tagged_flow(self):
        Run_Capture().response(_flow(run_id='run-1'))
        records = RUN_CAPTURE.records_for('run-1')
        assert len(records)                          == 1
        assert records[0]['run_id']                  == 'run-1'
        assert records[0]['request']['url']          == 'https://shop.test/pay'
        assert records[0]['request']['method']       == 'POST'
        assert records[0]['response']['status_code'] == 200

    def test__skips_untagged_flow(self):
        Run_Capture().response(_flow(run_id=None))
        assert RUN_CAPTURE.run_ids() == []

    def test__missing_response_does_not_crash(self):
        flow          = _flow(run_id='run-x')
        flow.response = None
        Run_Capture().response(flow)
        records = RUN_CAPTURE.records_for('run-x')
        assert len(records)                          == 1
        assert records[0]['response']['status_code'] is None

    def test__addons_export(self):
        assert len(addons) == 1
        assert isinstance(addons[0], Run_Capture)


class test_Run__Capture__Buffer(TestCase):

    def test__per_run_record_cap_evicts_oldest(self):
        buffer = Run__Capture__Buffer()
        for i in range(MAX_RECORDS_PER_RUN + 5):
            buffer.record('r', {'i': i})
        records = buffer.records_for('r')
        assert len(records)      == MAX_RECORDS_PER_RUN
        assert records[0]['i']   == 5                                               # first 5 evicted
        assert records[-1]['i']  == MAX_RECORDS_PER_RUN + 4

    def test__run_count_cap_evicts_oldest_run(self):
        buffer = Run__Capture__Buffer()
        for i in range(MAX_RUNS + 3):
            buffer.record(f'run-{i}', {'i': i})
        run_ids = buffer.run_ids()
        assert len(run_ids)              == MAX_RUNS
        assert 'run-0'                   not in run_ids                             # oldest 3 evicted
        assert 'run-2'                   not in run_ids
        assert f'run-{MAX_RUNS + 2}'     in run_ids

    def test__clear(self):
        buffer = Run__Capture__Buffer()
        buffer.record('a', {'x': 1})
        buffer.record('b', {'y': 2})
        buffer.clear('a')
        assert buffer.run_ids() == ['b']
        buffer.clear()
        assert buffer.run_ids() == []
