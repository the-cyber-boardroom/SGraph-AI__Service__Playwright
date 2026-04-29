# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__SG__Helper
# Real subclass overrides ec2_client(); no mocks. Mirrors the prom SG helper
# tests but expects port 443 (nginx TLS — operator UI + proxied mitmweb).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__SG__Helper                  import VIEWER_PORT_EXTERNAL, Vnc__SG__Helper


class _Fake_Boto_EC2:
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


class test_Vnc__SG__Helper(TestCase):

    def setUp(self):
        self.fake = _Fake_Boto_EC2()
        self.sg   = Vnc__SG__Helper()
        self.sg.ec2_client = lambda region: self.fake

    def test_port_constant_is_443(self):                                            # nginx TLS — chromium-VNC + mitmweb proxied
        assert VIEWER_PORT_EXTERNAL == 443

    def test_ensure_security_group__creates_when_missing(self):
        sg_id = self.sg.ensure_security_group('eu-west-2', 'vnc-quiet-fermi', '1.2.3.4')
        assert sg_id == 'sg-fake-new'
        ops = [c[0] for c in self.fake.calls]
        assert ops == ['describe_security_groups', 'create_security_group', 'authorize_security_group_ingress']

        create_kw = self.fake.calls[1][1]
        assert create_kw['GroupName']  == 'vnc-quiet-fermi-sg'
        assert 'vnc-quiet-fermi'       in create_kw['Description']
        assert create_kw['Description'].isascii()

        ingress_kw = self.fake.calls[2][1]
        perm = ingress_kw['IpPermissions'][0]
        assert perm['FromPort'] == VIEWER_PORT_EXTERNAL
        assert perm['ToPort']   == VIEWER_PORT_EXTERNAL
        assert perm['IpRanges'][0]['CidrIp'] == '1.2.3.4/32'

    def test_ensure_security_group__public_opens_to_zero_zero(self):                 # --open / public=True → 0.0.0.0/0 instead of caller /32
        sg_id = self.sg.ensure_security_group('eu-west-2', 'vnc-public', '1.2.3.4', public=True)
        assert sg_id == 'sg-fake-new'
        ingress_kw = self.fake.calls[2][1]
        perm = ingress_kw['IpPermissions'][0]
        assert perm['IpRanges'][0]['CidrIp'] == '0.0.0.0/0'

    def test_ensure_security_group__reuses_existing(self):
        self.fake.existing = [{'GroupId': 'sg-existing-vnc'}]
        sg_id = self.sg.ensure_security_group('eu-west-2', 'vnc-prod', '1.2.3.4')
        assert sg_id == 'sg-existing-vnc'
        ops = [c[0] for c in self.fake.calls]
        assert 'create_security_group' not in ops

    def test_ensure_security_group__duplicate_ingress_swallowed(self):
        self.fake.ingress_raise = RuntimeError('InvalidPermission.Duplicate')
        sg_id = self.sg.ensure_security_group('eu-west-2', 'vnc-prod', '1.2.3.4')
        assert sg_id == 'sg-fake-new'

    def test_ensure_security_group__other_ingress_errors_propagate(self):
        self.fake.ingress_raise = RuntimeError('AccessDenied')
        with self.assertRaises(RuntimeError):
            self.sg.ensure_security_group('eu-west-2', 'vnc-prod', '1.2.3.4')

    def test_delete_security_group__success(self):
        ok = self.sg.delete_security_group('eu-west-2', 'sg-to-delete')
        assert ok is True
        assert self.fake.deleted_ids == ['sg-to-delete']

    def test_delete_security_group__failure_returns_false(self):
        def boom(**kw): raise RuntimeError('DependencyViolation')
        self.fake.delete_security_group = boom
        assert self.sg.delete_security_group('eu-west-2', 'sg-still-attached') is False
