# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__Launch__Helper
# Real _Fake_Boto_EC2 subclass; no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import base64

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Launch__Helper import (DEFAULT_INSTANCE_TYPE      ,
                                                                                                Prometheus__Launch__Helper)


class _Fake_Boto_EC2:
    def __init__(self, instance_id='i-0123456789abcdef0', empty=False, raise_on_run=None):
        self.calls         = []
        self.instance_id   = instance_id
        self.empty         = empty
        self.raise_on_run  = raise_on_run
    def run_instances(self, **kw):
        self.calls.append(kw)
        if self.raise_on_run:
            raise self.raise_on_run
        if self.empty:
            return {'Instances': []}
        return {'Instances': [{'InstanceId': self.instance_id}]}


class test_Prometheus__Launch__Helper(TestCase):

    def setUp(self):
        self.fake     = _Fake_Boto_EC2()
        self.launcher = Prometheus__Launch__Helper()
        self.launcher.ec2_client = lambda region: self.fake

    def _run(self, **overrides):
        defaults = dict(region            = 'eu-west-2'                          ,
                        ami_id            = 'ami-0685f8dd865c8e389'              ,
                        security_group_id = 'sg-1234567890abcdef0'               ,
                        user_data         = '#!/usr/bin/env bash\necho hi\n'     ,
                        tags              = [{'Key': 'Name', 'Value': 'prometheus-x'}])
        defaults.update(overrides)
        return self.launcher.run_instance(**defaults)

    def test_run_instance__returns_instance_id(self):
        assert self._run() == 'i-0123456789abcdef0'

    def test_run_instance__base64_encodes_user_data(self):
        self._run(user_data='#!/usr/bin/env bash\nset -e\n')
        sent = self.fake.calls[0]['UserData']
        assert base64.b64decode(sent).decode('utf-8') == '#!/usr/bin/env bash\nset -e\n'

    def test_run_instance__attaches_security_group(self):
        self._run(security_group_id='sg-aaaaaaaaaaaaaaaaa')
        assert self.fake.calls[0]['SecurityGroupIds'] == ['sg-aaaaaaaaaaaaaaaaa']

    def test_run_instance__attaches_tag_specifications(self):
        tags = [{'Key': 'sg:purpose', 'Value': 'prometheus'},
                {'Key': 'sg:section', 'Value': 'prom'}      ]
        self._run(tags=tags)
        spec = self.fake.calls[0]['TagSpecifications'][0]
        assert spec['ResourceType'] == 'instance'
        assert spec['Tags']         == tags

    def test_run_instance__default_instance_type_is_t3_medium(self):                # Smaller than sp os (t3.large) — Prom is lighter
        assert DEFAULT_INSTANCE_TYPE == 't3.medium'
        self._run()
        assert self.fake.calls[0]['InstanceType'] == DEFAULT_INSTANCE_TYPE

    def test_run_instance__custom_instance_type(self):
        self._run(instance_type='t3.small')
        assert self.fake.calls[0]['InstanceType'] == 't3.small'

    def test_run_instance__instance_profile_optional(self):
        self._run()
        assert 'IamInstanceProfile' not in self.fake.calls[0]

    def test_run_instance__instance_profile_attached_when_provided(self):
        self._run(instance_profile_name='playwright-ec2')
        assert self.fake.calls[0]['IamInstanceProfile'] == {'Name': 'playwright-ec2'}

    def test_run_instance__min_max_count_pinned_to_one(self):                       # Single-node stack
        self._run()
        kw = self.fake.calls[0]
        assert kw['MinCount'] == 1
        assert kw['MaxCount'] == 1

    def test_run_instance__empty_response_raises(self):
        self.fake.empty = True
        with self.assertRaises(RuntimeError) as ctx:
            self._run()
        assert 'no Instances' in str(ctx.exception)

    def test_run_instance__boto_failure_propagates(self):
        self.fake.raise_on_run = RuntimeError('AccessDenied: not authorized')
        with self.assertRaises(RuntimeError):
            self._run()

    def test_run_instance__spot_market_options_sent_by_default(self):
        self._run()
        assert self.fake.calls[0]['InstanceMarketOptions'] == {'MarketType': 'spot'}

    def test_run_instance__no_spot_omits_market_options(self):
        self._run(use_spot=False)
        assert 'InstanceMarketOptions' not in self.fake.calls[0]
