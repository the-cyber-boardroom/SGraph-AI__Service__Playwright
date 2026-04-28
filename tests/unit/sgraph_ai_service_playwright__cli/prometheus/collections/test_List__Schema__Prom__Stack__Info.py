# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for List__Schema__Prom__Stack__Info
# Defensive: locks the expected_type so anything other than Schema__Prom__Stack__Info
# is rejected at append time.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Stack__Info import List__Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info


class test_List__Schema__Prom__Stack__Info(TestCase):

    def test__expected_type(self):
        assert List__Schema__Prom__Stack__Info.expected_type is Schema__Prom__Stack__Info

    def test__append_and_iterate(self):
        items = List__Schema__Prom__Stack__Info()
        items.append(Schema__Prom__Stack__Info(stack_name='prom-aaa'))
        items.append(Schema__Prom__Stack__Info(stack_name='prom-bbb'))
        assert len(items)                 == 2
        assert str(items[0].stack_name)   == 'prom-aaa'
        assert str(items[1].stack_name)   == 'prom-bbb'

    def test__rejects_wrong_type(self):
        items = List__Schema__Prom__Stack__Info()
        with self.assertRaises((TypeError, ValueError)):
            items.append('not-a-schema')
