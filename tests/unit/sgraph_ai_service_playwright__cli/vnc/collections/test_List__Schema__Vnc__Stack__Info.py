# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for List__Schema__Vnc__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info


class test_List__Schema__Vnc__Stack__Info(TestCase):

    def test__expected_type(self):
        assert List__Schema__Vnc__Stack__Info.expected_type is Schema__Vnc__Stack__Info

    def test__append_and_iterate(self):
        items = List__Schema__Vnc__Stack__Info()
        items.append(Schema__Vnc__Stack__Info(stack_name='vnc-aaa'))
        items.append(Schema__Vnc__Stack__Info(stack_name='vnc-bbb'))
        assert len(items)                 == 2
        assert str(items[0].stack_name)   == 'vnc-aaa'

    def test__rejects_wrong_type(self):
        items = List__Schema__Vnc__Stack__Info()
        with self.assertRaises((TypeError, ValueError)):
            items.append('not-a-schema')
