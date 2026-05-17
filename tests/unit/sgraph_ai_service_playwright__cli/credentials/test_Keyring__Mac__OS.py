# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Keyring__Mac__OS__In_Memory
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS import Keyring__Mac__OS__In_Memory


class test_Keyring__Mac__OS__In_Memory(TestCase):

    def test_get_missing_returns_none(self):
        k = Keyring__Mac__OS__In_Memory()
        assert k.get('sg.role', 'default') is None

    def test_set_and_get(self):
        k = Keyring__Mac__OS__In_Memory()
        k.set('sg.role', 'default', 'value')
        assert k.get('sg.role', 'default') == 'value'

    def test_delete_existing(self):
        k = Keyring__Mac__OS__In_Memory()
        k.set('sg.role', 'x', 'y')
        assert k.delete('sg.role', 'x') is True
        assert k.get('sg.role', 'x')    is None

    def test_delete_missing_returns_false(self):
        k = Keyring__Mac__OS__In_Memory()
        assert k.delete('sg.role', 'missing') is False

    def test_list_with_prefix(self):
        k = Keyring__Mac__OS__In_Memory()
        k.set('sg.role',  'default', 'v1')
        k.set('sg.role',  'admin',   'v2')
        k.set('sg.other', 'x',       'v3')
        entries  = k.list(prefix='sg.role')
        services = [str(e.service_name) for e in entries]
        accounts = [str(e.account)      for e in entries]
        assert all(s == 'sg.role' for s in services)
        assert set(accounts) == {'default', 'admin'}

    def test_list_prefix_all_sg(self):
        k = Keyring__Mac__OS__In_Memory()
        k.set('sg.role',  'default', 'v1')
        k.set('sg.aws',   'default', 'v2')
        k.set('other',    'x',       'v3')
        entries = k.list(prefix='sg.')
        assert len(entries) == 2
