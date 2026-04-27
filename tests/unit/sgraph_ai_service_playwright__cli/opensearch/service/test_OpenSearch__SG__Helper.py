# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__SG__Helper
# Real subclass overrides ec2_client(); no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__SG__Helper    import (DASHBOARDS_PORT_EXTERNAL,
                                                                                              OpenSearch__SG__Helper )


class _Fake_Boto_EC2:                                                               # Records every call; scriptable responses
    def __init__(self, existing=None, create_resp=None):
        self.calls         = []
        self.existing      = existing or []
        self.create_resp   = create_resp or {'GroupId': 'sg-fake-new'}
        self.deleted_ids   = []
        self.ingress_raise = None
    def describe_security_groups(self, **kw):
        self.calls.append(('describe_security_groups', kw))
        return {'SecurityGroups': self.existing}
    def create_security_group(self, **kw):
        self.calls.append(('create_security_group', kw))
        return self.create_resp
    def authorize_security_group_ingress(self, **kw):
        self.calls.append(('authorize_security_group_ingress', kw))
        if self.ingress_raise:
            raise self.ingress_raise
    def delete_security_group(self, **kw):
        self.calls.append(('delete_security_group', kw))
        self.deleted_ids.append(kw['GroupId'])


class test_OpenSearch__SG__Helper(TestCase):

    def setUp(self):
        self.fake = _Fake_Boto_EC2()
        self.sg   = OpenSearch__SG__Helper()
        self.sg.ec2_client = lambda region: self.fake

    def test_ensure_security_group__creates_when_missing(self):
        sg_id = self.sg.ensure_security_group('eu-west-2', 'os-quiet-fermi', '1.2.3.4')
        assert sg_id == 'sg-fake-new'
        ops = [c[0] for c in self.fake.calls]
        assert ops == ['describe_security_groups', 'create_security_group', 'authorize_security_group_ingress']

        create_kw = self.fake.calls[1][1]
        assert create_kw['GroupName']  == 'os-quiet-fermi-sg'                         # Per OS_NAMING.sg_name_for_stack
        assert 'os-quiet-fermi'        in create_kw['Description']
        assert create_kw['Description'].isascii()                                     # AWS rejects non-ASCII GroupDescription

        ingress_kw = self.fake.calls[2][1]
        perm = ingress_kw['IpPermissions'][0]
        assert perm['FromPort'] == DASHBOARDS_PORT_EXTERNAL
        assert perm['IpRanges'][0]['CidrIp'] == '1.2.3.4/32'

    def test_ensure_security_group__reuses_existing(self):
        self.fake.existing = [{'GroupId': 'sg-existing-os'}]
        sg_id = self.sg.ensure_security_group('eu-west-2', 'os-prod', '1.2.3.4')
        assert sg_id == 'sg-existing-os'
        ops = [c[0] for c in self.fake.calls]
        assert 'create_security_group' not in ops

    def test_ensure_security_group__duplicate_ingress_swallowed(self):
        self.fake.ingress_raise = RuntimeError('InvalidPermission.Duplicate: rule already exists')
        sg_id = self.sg.ensure_security_group('eu-west-2', 'os-prod', '1.2.3.4')
        assert sg_id == 'sg-fake-new'                                                # No raise — duplicate is the typical case

    def test_ensure_security_group__other_ingress_errors_propagate(self):
        self.fake.ingress_raise = RuntimeError('AccessDenied: cannot authorise')
        with self.assertRaises(RuntimeError):
            self.sg.ensure_security_group('eu-west-2', 'os-prod', '1.2.3.4')

    def test_delete_security_group__success(self):
        ok = self.sg.delete_security_group('eu-west-2', 'sg-to-delete')
        assert ok is True
        assert self.fake.deleted_ids == ['sg-to-delete']

    def test_delete_security_group__failure_returns_false(self):
        def boom(**kw): raise RuntimeError('DependencyViolation')
        self.fake.delete_security_group = boom
        assert self.sg.delete_security_group('eu-west-2', 'sg-still-attached') is False
