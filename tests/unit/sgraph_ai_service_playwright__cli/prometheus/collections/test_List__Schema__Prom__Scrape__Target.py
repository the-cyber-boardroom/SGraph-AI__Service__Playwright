# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for List__Schema__Prom__Scrape__Target
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target


class test_List__Schema__Prom__Scrape__Target(TestCase):

    def test__expected_type(self):
        assert List__Schema__Prom__Scrape__Target.expected_type is Schema__Prom__Scrape__Target

    def test__append_and_iterate(self):
        items = List__Schema__Prom__Scrape__Target()
        items.append(Schema__Prom__Scrape__Target(job_name='playwright'))
        items.append(Schema__Prom__Scrape__Target(job_name='cadvisor'))
        assert len(items)                 == 2
        assert str(items[0].job_name)     == 'playwright'
        assert str(items[1].job_name)     == 'cadvisor'

    def test__rejects_wrong_type(self):
        items = List__Schema__Prom__Scrape__Target()
        with self.assertRaises((TypeError, ValueError)):
            items.append('not-a-schema')
