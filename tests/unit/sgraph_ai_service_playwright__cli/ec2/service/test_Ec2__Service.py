# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Ec2__Service (Phase A step 3f)
# Exercises the service-level methods that the reduced typer commands now
# delegate to. AWS calls go through an injected fake Ec2__AWS__Client (real
# subclass, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client                  import (Ec2__AWS__Client    ,
                                                                                              TAG__DEPLOY_NAME_KEY,
                                                                                              TAG__SERVICE_KEY    ,
                                                                                              TAG__SERVICE_VALUE  )
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                      import Ec2__Service


class _Fake_EC2:                                                                    # In-memory stand-in matching the surface Ec2__AWS__Client touches
    def __init__(self):
        self.terminated = []
        self.details    = {}
    def instances_details(self, filters=None):
        return self.details
    def instance_terminate(self, instance_id):
        self.terminated.append(instance_id)


class _Fake_AWS_Client(Ec2__AWS__Client):                                           # Real Ec2__AWS__Client subclass — only ec2() is overridden
    def __init__(self, fake_ec2):
        super().__init__()
        self._fake = fake_ec2
    def ec2(self):
        return self._fake


def _details(deploy_name=''):
    tags = [{'Key': TAG__SERVICE_KEY, 'Value': TAG__SERVICE_VALUE}]
    if deploy_name:
        tags.append({'Key': TAG__DEPLOY_NAME_KEY, 'Value': deploy_name})
    return {'tags': tags, 'state': {'Name': 'running'}, 'public_ip': '1.2.3.4'}


class test_Ec2__Service__delete_all_instances(TestCase):

    def setUp(self):
        self.fake_ec2  = _Fake_EC2()
        self.fake_aws  = _Fake_AWS_Client(self.fake_ec2)
        self.service   = Ec2__Service()
        self.service.aws_client = lambda: self.fake_aws                             # Inject the fake — Type_Safe allows method override at instance level

    def test__no_instances__returns_empty_response(self):
        self.fake_ec2.details = {}
        result = self.service.delete_all_instances()
        assert str(result.target)              == ''
        assert list(result.terminated_instance_ids) == []
        assert self.fake_ec2.terminated         == []

    def test__multiple_instances__terminates_all_and_returns_their_ids(self):       # Safe_Str__Instance__Id requires the canonical i-{17 hex} shape
        ids = ('i-0123456789abcdef0', 'i-0123456789abcdef1', 'i-0123456789abcdef2')
        self.fake_ec2.details = {ids[0]: _details('happy-turing'),
                                 ids[1]: _details('quick-fermi'  ),
                                 ids[2]: _details('bold-curie'   )}
        result = self.service.delete_all_instances()
        assert sorted(str(iid) for iid in result.terminated_instance_ids) == sorted(ids)
        assert sorted(self.fake_ec2.terminated) == sorted(ids)
        assert str(result.target)               == ''                               # No single target on bulk delete
        assert str(result.deploy_name)          == ''
