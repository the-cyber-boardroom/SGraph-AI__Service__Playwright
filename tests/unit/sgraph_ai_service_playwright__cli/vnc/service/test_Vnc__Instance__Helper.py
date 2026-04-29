# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Instance__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE, TAG_STACK_NAME_KEY
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Instance__Helper            import INSTANCE_STATES_LIVE, Vnc__Instance__Helper


def _instance(iid='i-aaa', stack_name='', state='running'):
    tags = [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]
    if stack_name:
        tags.append({'Key': TAG_STACK_NAME_KEY, 'Value': stack_name})
    return {'InstanceId': iid, 'State': {'Name': state}, 'Tags': tags}


class _Fake_Boto_EC2:
    def __init__(self, instances=None):
        self.calls       = []
        self.instances   = instances or []
        self.terminated  = []
    def describe_instances(self, **kw):
        self.calls.append(('describe_instances', kw))
        return {'Reservations': [{'Instances': self.instances}]}
    def terminate_instances(self, **kw):
        self.calls.append(('terminate_instances', kw))
        self.terminated.extend(kw['InstanceIds'])


class test_Vnc__Instance__Helper(TestCase):

    def setUp(self):
        self.fake = _Fake_Boto_EC2()
        self.h    = Vnc__Instance__Helper()
        self.h.ec2_client = lambda region: self.fake

    def test_list_stacks__filters_by_purpose_and_live_states(self):
        self.fake.instances = [_instance('i-aaa', 'vnc-prod'), _instance('i-bbb', 'vnc-dev')]
        out = self.h.list_stacks('eu-west-2')
        assert sorted(out.keys()) == ['i-aaa', 'i-bbb']
        kw = self.fake.calls[0][1]
        filters = {f['Name']: f['Values'] for f in kw['Filters']}
        assert filters[f'tag:{TAG_PURPOSE_KEY}'] == [TAG_PURPOSE_VALUE]
        assert filters['instance-state-name']    == INSTANCE_STATES_LIVE

    def test_list_stacks__skips_instances_without_id(self):
        self.fake.instances = [{'State': {'Name': 'pending'}, 'Tags': []}]
        assert self.h.list_stacks('eu-west-2') == {}

    def test_find_by_stack_name__hit(self):
        self.fake.instances = [_instance('i-aaa', 'vnc-prod'), _instance('i-bbb', 'vnc-dev')]
        details = self.h.find_by_stack_name('eu-west-2', 'vnc-dev')
        assert details is not None
        assert details['InstanceId'] == 'i-bbb'

    def test_find_by_stack_name__miss(self):
        self.fake.instances = [_instance('i-aaa', 'vnc-prod')]
        assert self.h.find_by_stack_name('eu-west-2', 'no-such') is None

    def test_terminate_instance__success(self):
        assert self.h.terminate_instance('eu-west-2', 'i-aaa') is True
        assert self.fake.terminated == ['i-aaa']

    def test_terminate_instance__failure_returns_false(self):
        def boom(**kw): raise RuntimeError('NotAuthorized')
        self.fake.terminate_instances = boom
        assert self.h.terminate_instance('eu-west-2', 'i-aaa') is False
