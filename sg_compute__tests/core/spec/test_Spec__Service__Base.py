# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__Service__Base
# Verifies default health / exec / connect_target implementations.
# All tests use Fake__ objects — no AWS calls, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sg_compute.core.spec.Spec__Service__Base import Spec__Service__Base


# ── minimal fake CLI spec ─────────────────────────────────────────────────────

class _FakeCLISpec:
    spec_id    = 'docker'
    health_path = '/health'
    health_port = 80


class _FakeInfo:
    def __init__(self, instance_id='i-0abc', public_ip=''):
        self.instance_id = instance_id
        self.public_ip   = public_ip


# ── concrete subclass for testing ─────────────────────────────────────────────

class _Svc(Spec__Service__Base):

    _info_to_return = None
    _stacks         = []

    def cli_spec(self):
        return _FakeCLISpec()

    def setup(self):
        return self

    def create_stack(self, request):
        raise NotImplementedError

    def list_stacks(self, region):
        class _Listing:
            stacks = _Svc._stacks
            region = 'eu-west-2'
        return _Listing()

    def get_stack_info(self, region, name):
        return self._info_to_return

    def delete_stack(self, region, name):
        raise NotImplementedError


class test_Spec__Service__Base(TestCase):

    def setUp(self):
        self.svc = _Svc()

    def test_cli_spec__must_be_overridden_on_base(self):
        base = Spec__Service__Base()
        with pytest.raises(NotImplementedError):
            base.cli_spec()

    def test_connect_target__returns_instance_id(self):
        self.svc._info_to_return = _FakeInfo(instance_id='i-0deadbeef')
        result = self.svc.connect_target('eu-west-2', 'my-stack')
        assert result == 'i-0deadbeef'

    def test_connect_target__raises_when_no_stack(self):
        self.svc._info_to_return = None
        with pytest.raises(ValueError, match='no docker stack matched'):
            self.svc.connect_target('eu-west-2', 'ghost-stack')

    def test_health__returns_probe_with_no_public_ip(self):
        self.svc._info_to_return = _FakeInfo(instance_id='i-0abc', public_ip='')
        probe = self.svc.health('eu-west-2', 'my-stack', timeout_sec=0)
        assert probe.healthy is False
        assert 'no public IP' in str(probe.last_error)

    def test_health__returns_probe_when_stack_missing(self):
        self.svc._info_to_return = None
        probe = self.svc.health('eu-west-2', 'ghost', timeout_sec=0)
        assert probe.healthy is False
        assert 'no stack matched' in str(probe.last_error)

    def test_health__elapsed_ms_is_populated(self):
        self.svc._info_to_return = _FakeInfo(public_ip='')
        probe = self.svc.health('eu-west-2', 'my-stack', timeout_sec=0)
        assert probe.elapsed_ms >= 0

    def test_exec__raises_when_stack_missing(self):
        self.svc._info_to_return = None
        with pytest.raises(ValueError, match='no stack matched'):
            self.svc.exec('eu-west-2', 'ghost', 'echo hi')
