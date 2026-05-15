# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__Auto_DNS
# In-memory composition with lightweight fakes for the three dev-branch service
# classes: Route53__AWS__Client, Route53__Zone__Resolver,
# Route53__Authoritative__Checker. No mocks / patches — the helper exposes
# factory seams that the test substitutes directly.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Auto_DNS__Result import Schema__Vault_App__Auto_DNS__Result
from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS                  import Vault_App__Auto_DNS


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _Fake_Change:
    def __init__(self, change_id='/change/CABC', status='INSYNC', submitted_at='2026-05-15T00:00:00Z'):
        self.change_id    = change_id
        self.status       = status
        self.submitted_at = submitted_at


class _Fake_Zone:
    def __init__(self, zone_id='/hostedzone/Z123', name='sg-compute.sgraph.ai'):
        self.zone_id = zone_id
        self.name    = name


class _Fake_Auth_Result:
    def __init__(self, passed=True, agreed_count=4, total_count=4):
        self.passed       = passed
        self.agreed_count = agreed_count
        self.total_count  = total_count


class _Fake_AWS_Client:
    def __init__(self, insync_after_polls=0, upsert_raises=None):
        self.insync_after_polls = insync_after_polls
        self.upsert_raises      = upsert_raises
        self.upserts            = []                                            # captured call args
        self.wait_calls         = []

    def upsert_record(self, zone_id, name, rtype, values, ttl=60):
        if self.upsert_raises is not None:
            raise self.upsert_raises
        self.upserts.append(dict(zone_id=zone_id, name=name, rtype=rtype, values=list(values), ttl=ttl))
        return _Fake_Change(change_id='/change/CFOO', status='PENDING')

    def wait_for_change(self, change_id, timeout=120, poll_interval=2, on_poll=None):
        self.wait_calls.append(dict(change_id=change_id, timeout=timeout, poll_interval=poll_interval))
        if self.insync_after_polls < 0:                                         # negative = never reach INSYNC inside the budget
            return _Fake_Change(change_id=change_id, status='PENDING')
        return _Fake_Change(change_id=change_id, status='INSYNC')


class _Fake_Zone_Resolver:
    def __init__(self, zone=None, raises=None):
        self._zone   = zone or _Fake_Zone()
        self._raises = raises

    def resolve_zone_for_fqdn(self, fqdn):
        if self._raises is not None:
            raise self._raises
        return self._zone


class _Fake_Auth_Checker:
    def __init__(self, result=None):
        self._result = result or _Fake_Auth_Result()

    def check(self, zone_id, name, rtype, expected=''):
        return self._result


# ── Helper to wire fakes through the factory seams ────────────────────────────

def _build(auto_dns_kwargs=None, **fakes):
    aws    = fakes.get('aws')    or _Fake_AWS_Client()
    zone_r = fakes.get('zone_r') or _Fake_Zone_Resolver()
    auth_c = fakes.get('auth_c') or _Fake_Auth_Checker()
    helper = Vault_App__Auto_DNS()
    helper._aws_client_factory     = lambda: aws
    helper._zone_resolver_factory  = lambda client: zone_r
    helper._auth_checker_factory   = lambda client: auth_c
    return helper, aws


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestVaultAppAutoDNS:

    def test_happy_path_upserts_waits_for_insync_and_runs_auth_check(self):
        helper, aws = _build()
        progress = []
        result   = helper.run(fqdn='warm-bohr.sg-compute.sgraph.ai',
                              public_ip='18.175.166.157',
                              on_progress=lambda stage, detail: progress.append(stage))
        assert isinstance(result, Schema__Vault_App__Auto_DNS__Result)
        assert result.fqdn               == 'warm-bohr.sg-compute.sgraph.ai'
        assert result.public_ip          == '18.175.166.157'
        assert result.zone_name          == 'sg-compute.sgraph.ai'
        assert result.zone_id            == '/hostedzone/Z123'
        assert result.change_id          == '/change/CFOO'
        assert result.insync             is True
        assert result.authoritative_pass is True
        assert result.error              == ''
        assert result.elapsed_ms         >= 0
        assert progress == ['resolving-zone', 'upserting', 'waiting-insync', 'checking-auth', 'done']
        assert aws.upserts == [dict(zone_id='/hostedzone/Z123', name='warm-bohr.sg-compute.sgraph.ai',
                                     rtype='A', values=['18.175.166.157'], ttl=60)]

    def test_failure_in_zone_resolver_captured_in_error_field(self):
        helper, aws = _build(zone_r=_Fake_Zone_Resolver(raises=ValueError('no matching zone')))
        result      = helper.run(fqdn='unknown.example.com', public_ip='1.2.3.4')
        assert result.error           == 'ValueError: no matching zone'
        assert result.change_id       == ''                                     # never reached upsert
        assert result.insync          is False
        assert aws.upserts            == []

    def test_failure_in_upsert_captured_in_error_field_without_raising(self):
        # The CLI runs this on a thread — Auto_DNS must NEVER raise out.
        helper, aws = _build(aws=_Fake_AWS_Client(upsert_raises=RuntimeError('Route53 throttled')))
        result      = helper.run(fqdn='warm-bohr.sg-compute.sgraph.ai', public_ip='18.0.0.1')
        assert result.error == 'RuntimeError: Route53 throttled'
        assert result.insync is False

    def test_insync_timeout_is_a_failure_not_an_exception(self):
        helper, aws = _build(aws=_Fake_AWS_Client(insync_after_polls=-1))
        result      = helper.run(fqdn='warm-bohr.sg-compute.sgraph.ai', public_ip='18.0.0.1')
        assert result.change_id          == '/change/CFOO'                      # upsert happened
        assert result.insync             is False
        assert result.authoritative_pass is False                               # never got to the auth check
        assert 'did not reach INSYNC' in result.error

    def test_authoritative_disagreement_is_a_failure(self):
        helper, aws = _build(auth_c=_Fake_Auth_Checker(_Fake_Auth_Result(passed=False, agreed_count=2, total_count=4)))
        result      = helper.run(fqdn='warm-bohr.sg-compute.sgraph.ai', public_ip='18.0.0.1')
        assert result.insync             is True
        assert result.authoritative_pass is False
        assert 'only 2/4 authoritative nameservers' in result.error
        assert '18.0.0.1' in result.error

    def test_wait_for_change_called_with_expected_timeout_and_poll(self):
        from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS import AUTO_DNS__INSYNC_TIMEOUT_SEC, AUTO_DNS__INSYNC_POLL_SEC
        helper, aws = _build()
        helper.run(fqdn='warm-bohr.sg-compute.sgraph.ai', public_ip='18.0.0.1')
        assert aws.wait_calls == [dict(change_id='/change/CFOO',
                                       timeout=AUTO_DNS__INSYNC_TIMEOUT_SEC,
                                       poll_interval=AUTO_DNS__INSYNC_POLL_SEC)]
