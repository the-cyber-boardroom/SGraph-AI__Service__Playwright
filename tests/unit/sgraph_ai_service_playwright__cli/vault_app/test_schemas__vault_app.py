# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for vault_app schemas, enums, and state model
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State    import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Health      import Schema__Vault_App__Health
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Create__Request  import Schema__Vault_App__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Create__Response import Schema__Vault_App__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Delete__Response import Schema__Vault_App__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Info import Schema__Vault_App__Stack__Info
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__List import Schema__Vault_App__Stack__List


class test_Schema__Vault_App__Health(TestCase):

    def test__defaults(self):
        h = Schema__Vault_App__Health()
        assert h.vault_ok      is False
        assert h.playwright_ok is False
        assert h.state         == Enum__Vault_App__Stack__State.UNKNOWN
        assert str(h.error)    == ''

    def test__round_trip(self):
        h = Schema__Vault_App__Health(stack_name='va-prod',
                                       state=Enum__Vault_App__Stack__State.READY,
                                       vault_ok=True, playwright_ok=True)
        again = Schema__Vault_App__Health.from_json(h.json())
        assert str(again.stack_name)  == 'va-prod'
        assert again.state            == Enum__Vault_App__Stack__State.READY
        assert again.vault_ok         is True
        assert again.playwright_ok    is True


class test_Schema__Vault_App__Stack__Create__Request(TestCase):

    def test__defaults_allow_empty_create(self):
        r = Schema__Vault_App__Stack__Create__Request()
        assert str(r.stack_name)    == ''
        assert str(r.region)        == ''
        assert str(r.access_token)  == ''
        assert r.max_hours          == 4
        assert r.use_spot           is True
        assert str(r.storage_mode)  == 'disk'

    def test__round_trip(self):
        r = Schema__Vault_App__Stack__Create__Request(
            stack_name='va-test', max_hours=2, use_spot=False
        )
        again = Schema__Vault_App__Stack__Create__Request.from_json(r.json())
        assert str(again.stack_name) == 'va-test'
        assert again.max_hours       == 2
        assert again.use_spot        is False


class test_Schema__Vault_App__Stack__List(TestCase):

    def test__empty_list(self):
        sl = Schema__Vault_App__Stack__List()
        assert list(sl.stacks) == []

    def test__round_trip_with_item(self):
        info = Schema__Vault_App__Stack__Info(stack_name='va-alpha',
                                               instance_id='i-0abc123')
        sl   = Schema__Vault_App__Stack__List(region='eu-west-2')
        sl.stacks.append(info)
        again = Schema__Vault_App__Stack__List.from_json(sl.json())
        assert str(again.region)            == 'eu-west-2'
        assert len(list(again.stacks))      == 1
        assert str(again.stacks[0].stack_name) == 'va-alpha'


class test_Schema__Vault_App__Stack__Delete__Response(TestCase):

    def test__empty_on_miss(self):
        r = Schema__Vault_App__Stack__Delete__Response()
        assert str(r.target)               == ''
        assert str(r.stack_name)           == ''
        assert list(r.terminated_instance_ids) == []


class test_Enum__Vault_App__Stack__State(TestCase):

    def test__str_values(self):
        assert str(Enum__Vault_App__Stack__State.PENDING)     == 'pending'
        assert str(Enum__Vault_App__Stack__State.RUNNING)     == 'running'
        assert str(Enum__Vault_App__Stack__State.READY)       == 'ready'
        assert str(Enum__Vault_App__Stack__State.TERMINATING) == 'terminating'
        assert str(Enum__Vault_App__Stack__State.TERMINATED)  == 'terminated'
        assert str(Enum__Vault_App__Stack__State.UNKNOWN)     == 'unknown'
