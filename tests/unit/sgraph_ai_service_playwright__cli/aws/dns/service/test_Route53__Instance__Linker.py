# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__Instance__Linker
# Fakes boto3.client('ec2') by subclassing Route53__Instance__Linker and
# overriding ec2_client() to return a canned stub.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import pytest

from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Instance__Linker import Route53__Instance__Linker


# ── Fake EC2 client ───────────────────────────────────────────────────────────

def _make_instance(instance_id, name, public_ip=None, state='running',
                   launch_time='2026-05-15T10:00:00Z', extra_tags=None):
    tags = [{'Key': 'Name', 'Value': name}]
    if extra_tags:
        tags.extend(extra_tags)
    inst = {'InstanceId': instance_id, 'Tags': tags,
            'State': {'Name': state}, 'LaunchTime': launch_time}
    if public_ip:
        inst['PublicIpAddress'] = public_ip
    return inst


_INST_A = _make_instance('i-aaa', 'quiet-fermi',  '203.0.113.10',
                          launch_time='2026-05-15T11:00:00Z',
                          extra_tags=[{'Key': 'sg:stack', 'Value': 'fermi'}])
_INST_B = _make_instance('i-bbb', 'loud-bohr',    '203.0.113.20',
                          launch_time='2026-05-15T09:00:00Z',
                          extra_tags=[{'Key': 'sg:stack', 'Value': 'bohr'}])
_INST_NO_IP = _make_instance('i-ccc', 'no-ip-inst', None,
                              extra_tags=[{'Key': 'sg:stack', 'Value': 'test'}])
_INST_SG_COMPUTE = _make_instance('i-ddd', 'warm-bohr',   '203.0.113.30',                # Mirrors a real sg_compute platform stack (vault_app/ollama) — Purpose=ephemeral-ec2 instead of sg:* prefix
                                   launch_time='2026-05-15T12:00:00Z',
                                   extra_tags=[{'Key': 'Purpose'  , 'Value': 'ephemeral-ec2'},
                                               {'Key': 'StackName', 'Value': 'warm-bohr'  }])


class _Fake_EC2_Client:
    def __init__(self, instances):
        self._instances = instances

    def describe_instances(self, InstanceIds=None, Filters=None):
        result = []
        for inst in self._instances:
            if InstanceIds and inst['InstanceId'] not in InstanceIds:
                continue
            if Filters:
                match = True
                for f in Filters:
                    key = f['Name']
                    vals = f['Values']
                    if key == 'tag:Name':
                        tag_names = [t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name']
                        if not any(n in vals for n in tag_names):
                            match = False
                    elif key == 'instance-state-name':
                        if inst['State']['Name'] not in vals:
                            match = False
                if not match:
                    continue
            result.append(inst)
        return {'Reservations': [{'Instances': result}]}


class _Fake_Route53__Instance__Linker(Route53__Instance__Linker):
    _ec2_instances: list = None

    def ec2_client(self):
        return _Fake_EC2_Client(self._ec2_instances or [])


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__Instance__Linker(TestCase):

    def setUp(self):
        self.linker = _Fake_Route53__Instance__Linker(_ec2_instances=[_INST_A, _INST_B, _INST_NO_IP])

    # ── resolve_instance by id ────────────────────────────────────────────────

    def test__resolve_instance__by_id__returns_instance(self):
        inst = self.linker.resolve_instance('i-aaa')
        assert inst['InstanceId'] == 'i-aaa'

    def test__resolve_instance__by_id__not_found__raises(self):
        with pytest.raises(ValueError, match='No running instance'):
            self.linker.resolve_instance('i-zzz')

    # ── resolve_instance by Name tag ──────────────────────────────────────────

    def test__resolve_instance__by_name__returns_instance(self):
        inst = self.linker.resolve_instance('quiet-fermi')
        assert inst['InstanceId'] == 'i-aaa'

    def test__resolve_instance__by_name__not_found__raises(self):
        with pytest.raises(ValueError, match='No running instance'):
            self.linker.resolve_instance('nonexistent-name')

    # ── resolve_latest ────────────────────────────────────────────────────────

    def test__resolve_latest__returns_most_recent_sg_tagged_instance(self):
        inst = self.linker.resolve_latest()
        assert inst['InstanceId'] == 'i-aaa'                                     # i-aaa has LaunchTime 11:00 > i-bbb 09:00

    def test__resolve_latest__no_sg_instances__raises(self):
        linker = _Fake_Route53__Instance__Linker(_ec2_instances=[])
        with pytest.raises(ValueError, match='No running SG-managed instance'):
            linker.resolve_latest()

    def test__resolve_latest__matches_sg_compute_platform_tag(self):                      # Purpose=ephemeral-ec2 (vault_app / ollama / etc.) must also count
        linker = _Fake_Route53__Instance__Linker(_ec2_instances=[_INST_SG_COMPUTE])
        inst   = linker.resolve_latest()
        assert inst['InstanceId'] == 'i-ddd'

    def test__resolve_latest__picks_most_recent_across_tag_styles(self):                  # sg_compute Purpose=ephemeral-ec2 instance is newer (12:00) than legacy sg:* one (11:00)
        linker = _Fake_Route53__Instance__Linker(_ec2_instances=[_INST_A, _INST_B, _INST_SG_COMPUTE])
        inst   = linker.resolve_latest()
        assert inst['InstanceId'] == 'i-ddd'

    # ── get_public_ip ─────────────────────────────────────────────────────────

    def test__get_public_ip__returns_ip(self):
        ip = self.linker.get_public_ip(_INST_A)
        assert ip == '203.0.113.10'

    def test__get_public_ip__no_ip__raises(self):
        with pytest.raises(ValueError, match='no public IP'):
            self.linker.get_public_ip(_INST_NO_IP)

    # ── get_name_tag ──────────────────────────────────────────────────────────

    def test__get_name_tag__returns_name_tag(self):
        name = self.linker.get_name_tag(_INST_A)
        assert name == 'quiet-fermi'

    def test__get_name_tag__no_name_tag__falls_back_to_instance_id(self):
        inst_no_name = {'InstanceId': 'i-xyz', 'Tags': []}
        name         = self.linker.get_name_tag(inst_no_name)
        assert name == 'i-xyz'
