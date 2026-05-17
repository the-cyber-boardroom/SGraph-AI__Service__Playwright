# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Keyring__Mac__OS (Phase A)
# All tests use Keyring__Mac__OS__In_Memory — no real Keychain calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.osx.keyring.schemas.Schema__Keyring__Entry             import Schema__Keyring__Entry
from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS                   import Keyring__Mac__OS
from tests.unit.sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS__In_Memory import Keyring__Mac__OS__In_Memory


def _keyring() -> Keyring__Mac__OS__In_Memory:
    return Keyring__Mac__OS__In_Memory()


class test_Keyring__Mac__OS__set_and_get(TestCase):

    def test__get_unknown_returns_none(self):
        kr    = _keyring()
        value = kr.get('sg.test.svc', 'account')
        assert value is None

    def test__set_then_get_round_trips(self):
        kr    = _keyring()
        ok    = kr.set('sg.test.svc', 'account', 'my-secret')
        assert ok is True
        value = kr.get('sg.test.svc', 'account')
        assert value == 'my-secret'

    def test__set_overwrites_existing_value(self):
        kr = _keyring()
        kr.set('sg.svc', 'acct', 'first')
        kr.set('sg.svc', 'acct', 'second')
        assert kr.get('sg.svc', 'acct') == 'second'

    def test__different_accounts_are_independent(self):
        kr = _keyring()
        kr.set('sg.svc', 'acct-a', 'value-a')
        kr.set('sg.svc', 'acct-b', 'value-b')
        assert kr.get('sg.svc', 'acct-a') == 'value-a'
        assert kr.get('sg.svc', 'acct-b') == 'value-b'

    def test__different_services_are_independent(self):
        kr = _keyring()
        kr.set('sg.svc.one', 'acct', 'val-one')
        kr.set('sg.svc.two', 'acct', 'val-two')
        assert kr.get('sg.svc.one', 'acct') == 'val-one'
        assert kr.get('sg.svc.two', 'acct') == 'val-two'


class test_Keyring__Mac__OS__delete(TestCase):

    def test__delete_existing_returns_true(self):
        kr = _keyring()
        kr.set('sg.svc', 'acct', 'v')
        ok = kr.delete('sg.svc', 'acct')
        assert ok is True

    def test__after_delete_get_returns_none(self):
        kr = _keyring()
        kr.set('sg.svc', 'acct', 'v')
        kr.delete('sg.svc', 'acct')
        assert kr.get('sg.svc', 'acct') is None

    def test__delete_nonexistent_returns_false(self):
        kr = _keyring()
        ok = kr.delete('sg.svc', 'acct')
        assert ok is False


class test_Keyring__Mac__OS__list(TestCase):

    def test__empty_keyring_returns_empty_list(self):
        kr      = _keyring()
        entries = kr.list(prefix='sg.')
        assert entries == []

    def test__list_returns_matching_prefix_entries(self):
        kr = _keyring()
        kr.set('sg.config.role.admin', 'config', '{}')
        kr.set('sg.config.role.dev',   'config', '{}')
        entries = kr.list(prefix='sg.config.role.')
        assert len(entries) == 2

    def test__list_filters_by_prefix(self):
        kr = _keyring()
        kr.set('sg.config.role.admin', 'config', '{}')
        kr.set('other.service',         'acct',   '{}')
        entries = kr.list(prefix='sg.')
        assert len(entries) == 1
        assert str(entries[0].service_name) == 'sg.config.role.admin'

    def test__list_entries_are_schema_keyring_entry(self):
        kr = _keyring()
        kr.set('sg.aws.admin', 'access_key', 'AKIA...')
        entries = kr.list(prefix='sg.')
        assert isinstance(entries[0], Schema__Keyring__Entry)


class test_Keyring__Mac__OS__search(TestCase):

    def test__search_returns_entries_matching_service_name(self):
        kr = _keyring()
        kr.set('sg.aws.admin', 'access_key', 'AKIA...')
        kr.set('sg.aws.admin', 'secret_key', 'shhh...')
        entries = kr.search('sg.aws.admin')
        accounts = [str(e.account) for e in entries]
        assert 'access_key' in accounts
        assert 'secret_key' in accounts

    def test__search_different_service_returns_empty(self):
        kr = _keyring()
        kr.set('sg.aws.admin', 'access_key', 'AKIA...')
        entries = kr.search('sg.aws.dev')
        assert entries == []
