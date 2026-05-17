# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Service stop / start + DNS-delete helpers
# No mocks, no patches (except monkeypatch for the Auto_DNS import).
# All AWS-touching methods overridden in proper subclasses so Type_Safe's
# type-guard stays happy.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper                 import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper                       import EC2__SG__Helper
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Stop__Response   import Schema__Vault_App__Stop__Response
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Start__Response  import Schema__Vault_App__Start__Response
from sg_compute_specs.vault_app.service.Vault_App__AWS__Client              import Vault_App__AWS__Client
from sg_compute_specs.vault_app.service.Vault_App__Service                  import Vault_App__Service
from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper            import (TAG_TLS_HOSTNAME,
                                                                                    TAG_WITH_PLAYWRIGHT)


# ── Constants ─────────────────────────────────────────────────────────────────

REGION     = 'eu-west-2'
STACK_NAME = 'sara-cv'
IID        = 'i-0abc123def456'
FQDN       = 'sara-cv.aws.sg-labs.app'
PUBLIC_IP  = '1.2.3.4'
SG_ID      = 'sg-abc123'


# ── In-memory EC2__Instance__Helper ──────────────────────────────────────────

class _Instance_Helper__In_Memory(EC2__Instance__Helper):
    def __init__(self, details=None, stop_ok=True, start_ok=True):
        super().__init__()
        self._details   = details
        self.stop_ok    = stop_ok
        self.start_ok   = start_ok
        self.stopped    = []
        self.started    = []
        self.terminated = []

    def find_by_stack_name(self, region, stack_name):
        return self._details

    def stop(self, region, iid):
        self.stopped.append(iid)
        return self.stop_ok

    def start(self, region, iid):
        self.started.append(iid)
        return self.start_ok

    def terminate(self, region, iid):
        self.terminated.append(iid)
        return True

    def get_public_ip(self, region, iid):
        return PUBLIC_IP

    def wait_for_running(self, region, iid, timeout_sec=300, poll_sec=10):
        return True


# ── In-memory EC2__SG__Helper ─────────────────────────────────────────────────

class _SG_Helper__In_Memory(EC2__SG__Helper):
    def delete_security_group(self, region, sg_id):
        pass


# ── In-memory Vault_App__AWS__Client ─────────────────────────────────────────

class _VA_AWS_Client__In_Memory(Vault_App__AWS__Client):
    def setup_in_memory(self, details=None, stop_ok=True, start_ok=True) -> '_VA_AWS_Client__In_Memory':
        from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import EC2__Tags__Builder
        from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper import STACK_TYPE
        self.instance = _Instance_Helper__In_Memory(details=details, stop_ok=stop_ok, start_ok=start_ok)
        self.sg       = _SG_Helper__In_Memory()
        self.tags     = EC2__Tags__Builder(stack_type=STACK_TYPE)
        return self


# ── Fake Route53 client (not a Type_Safe subclass — accessed only via lambda) ──

class _Fake_R53:
    def __init__(self, delete_raises=None):
        self.deleted       = []
        self.delete_raises = delete_raises

    def delete_record(self, zone, fqdn, record_type):
        if self.delete_raises:
            raise self.delete_raises
        self.deleted.append((zone, fqdn))


# ── Instance details factory ───────────────────────────────────────────────────

def _make_details(fqdn=''):
    tags = [{'Key': 'sg:stack-name',     'Value': STACK_NAME},
            {'Key': 'sg:stack-type',     'Value': 'vault-app'},
            {'Key': TAG_WITH_PLAYWRIGHT, 'Value': 'false'}]
    if fqdn:
        tags.append({'Key': TAG_TLS_HOSTNAME, 'Value': fqdn})
    return {
        'InstanceId'     : IID,
        'SecurityGroups' : [{'GroupId': SG_ID}],
        'Tags'           : tags,
    }


# ── Build a wired-up service ───────────────────────────────────────────────────

def _build_svc(details=None, stop_ok=True, start_ok=True, delete_raises=None):
    svc            = Vault_App__Service()
    svc.aws_client = _VA_AWS_Client__In_Memory().setup_in_memory(
                         details=details, stop_ok=stop_ok, start_ok=start_ok)
    fake_r53       = _Fake_R53(delete_raises=delete_raises)
    svc._r53_client_factory = lambda: fake_r53
    return svc, fake_r53


# ── Tests: tls_hostname_from_details ──────────────────────────────────────────

class TestTlsHostnameFromDetails:
    def test_returns_fqdn_when_tag_present(self):
        svc, _ = _build_svc()
        assert svc.tls_hostname_from_details(_make_details(fqdn=FQDN)) == FQDN

    def test_returns_empty_when_tag_absent(self):
        svc, _ = _build_svc()
        assert svc.tls_hostname_from_details(_make_details(fqdn=''))   == ''


# ── Tests: delete_per_slug_a_record ───────────────────────────────────────────

class TestDeletePerSlugARecord:
    def test_deletes_when_fqdn_present(self):
        svc, r53 = _build_svc()
        ok       = svc.delete_per_slug_a_record(REGION, _make_details(fqdn=FQDN))
        assert ok is True
        assert len(r53.deleted) == 1
        _, deleted_fqdn = r53.deleted[0]
        assert deleted_fqdn == FQDN

    def test_returns_false_when_no_fqdn(self):
        svc, r53 = _build_svc()
        ok       = svc.delete_per_slug_a_record(REGION, _make_details(fqdn=''))
        assert ok is False
        assert r53.deleted == []

    def test_returns_false_when_r53_raises(self):
        svc, r53 = _build_svc(delete_raises=ValueError('not found'))
        ok       = svc.delete_per_slug_a_record(REGION, _make_details(fqdn=FQDN))
        assert ok is False  # exception caught — does not propagate


# ── Tests: stop_stack ─────────────────────────────────────────────────────────

class TestStopStack:
    def test_stop_happy_path_with_dns(self):
        details  = _make_details(fqdn=FQDN)
        svc, r53 = _build_svc(details=details)
        resp     = svc.stop_stack(REGION, STACK_NAME)
        assert isinstance(resp, Schema__Vault_App__Stop__Response)
        assert resp.stopped     is True
        assert resp.dns_deleted is True
        assert IID in svc.aws_client.instance.stopped
        assert len(r53.deleted) == 1

    def test_stop_happy_path_without_dns(self):
        details  = _make_details(fqdn='')
        svc, r53 = _build_svc(details=details)
        resp     = svc.stop_stack(REGION, STACK_NAME)
        assert resp.stopped     is True
        assert resp.dns_deleted is False
        assert r53.deleted      == []

    def test_stop_not_found(self):
        svc, _ = _build_svc(details=None)
        resp   = svc.stop_stack(REGION, STACK_NAME)
        assert resp.stopped     is False
        assert resp.dns_deleted is False
        assert 'not found' in resp.message

    def test_stop_ec2_fails(self):
        details  = _make_details(fqdn=FQDN)
        svc, r53 = _build_svc(details=details, stop_ok=False)
        resp     = svc.stop_stack(REGION, STACK_NAME)
        assert resp.stopped is False
        assert 'failed' in resp.message
        # DNS delete was still attempted before the EC2 stop call
        assert len(r53.deleted) == 1

    def test_stop_dns_delete_failure_does_not_block_ec2_stop(self):
        details  = _make_details(fqdn=FQDN)
        svc, _   = _build_svc(details=details, delete_raises=Exception('R53 error'))
        resp     = svc.stop_stack(REGION, STACK_NAME)
        assert resp.stopped     is True    # EC2 stop still proceeded
        assert resp.dns_deleted is False   # DNS delete reported as failed


# ── Tests: start_stack ────────────────────────────────────────────────────────

class TestStartStack:
    def test_start_happy_path(self):
        details = _make_details(fqdn=FQDN)
        svc, _  = _build_svc(details=details)
        resp    = svc.start_stack(REGION, STACK_NAME)
        assert isinstance(resp, Schema__Vault_App__Start__Response)
        assert resp.started is True
        assert IID in svc.aws_client.instance.started

    def test_start_not_found(self):
        svc, _ = _build_svc(details=None)
        resp   = svc.start_stack(REGION, STACK_NAME)
        assert resp.started is False
        assert 'not found' in resp.message

    def test_start_ec2_fails(self):
        details = _make_details(fqdn=FQDN)
        svc, _  = _build_svc(details=details, start_ok=False)
        resp    = svc.start_stack(REGION, STACK_NAME)
        assert resp.started is False
        assert 'failed' in resp.message

    def test_start_with_wait_upserts_dns(self):
        details  = _make_details(fqdn=FQDN)
        svc, _   = _build_svc(details=details)
        upserted = []

        class _Fake_Auto_DNS:
            class _FakeResult:
                error = ''
            def run(self, fqdn, public_ip):
                upserted.append((fqdn, public_ip))
                return self._FakeResult()

        svc._auto_dns_factory = lambda: _Fake_Auto_DNS()
        resp = svc.start_stack(REGION, STACK_NAME, wait_running=True)
        assert resp.started      is True
        assert resp.public_ip    == PUBLIC_IP
        assert resp.dns_upserted is True
        assert resp.fqdn         == FQDN
        assert upserted          == [(FQDN, PUBLIC_IP)]

    def test_start_without_wait_does_not_upsert_dns(self):
        details  = _make_details(fqdn=FQDN)
        svc, r53 = _build_svc(details=details)
        resp     = svc.start_stack(REGION, STACK_NAME, wait_running=False)
        assert resp.started      is True
        assert resp.dns_upserted is False
        assert r53.deleted       == []  # no DNS ops at all in no-wait mode
