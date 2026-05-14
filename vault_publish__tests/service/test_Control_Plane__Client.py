# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Control_Plane__Client (no mocks, no patches)
# Key generation and the single-use ledger — a control-plane key is accepted
# exactly once.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Safe_Str__Instance__Id     import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Slug             import Safe_Str__Slug
from vault_publish.schemas.Schema__Provisioning__Plan import Schema__Provisioning__Plan
from vault_publish.service.Control_Plane__Client      import Control_Plane__Client

SLUG        = Safe_Str__Slug('sara-cv')
INSTANCE_ID = Safe_Str__Instance__Id('i-abc123')


class test_Control_Plane__Client(TestCase):

    def setUp(self):
        self.client = Control_Plane__Client()

    def test_generate_key_is_non_empty(self):
        assert str(self.client.generate_key()) != ''

    def test_generate_key_is_unique(self):
        assert str(self.client.generate_key()) != str(self.client.generate_key())

    def test_provision_succeeds_once(self):
        key = self.client.generate_key()
        assert self.client.provision(SLUG, INSTANCE_ID, key, Schema__Provisioning__Plan()) is True

    def test_provision_rejects_reused_key(self):                             # single-use ledger
        key = self.client.generate_key()
        self.client.provision(SLUG, INSTANCE_ID, key, Schema__Provisioning__Plan())
        assert self.client.provision(SLUG, INSTANCE_ID, key, Schema__Provisioning__Plan()) is False

    def test_provisioned_plan_is_recorded(self):
        key  = self.client.generate_key()
        plan = Schema__Provisioning__Plan()
        self.client.provision(SLUG, INSTANCE_ID, key, plan)
        assert self.client.provisioned_plan(SLUG) is plan

    def test_provisioned_plan_none_when_absent(self):
        assert self.client.provisioned_plan(SLUG) is None
