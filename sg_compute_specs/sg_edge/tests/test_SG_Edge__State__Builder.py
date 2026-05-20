# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for SG_Edge__State__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.service.SG_Edge__State__Builder        import SG_Edge__State__Builder


class test_SG_Edge__State__Builder(TestCase):

    def setUp(self):
        self.builder = SG_Edge__State__Builder()

    def test_build__emits_canonical_order(self):
        record = Schema__SG_Edge__State__Record(zero_streak=2, updated=1747700000)
        assert self.builder.build(record) == 'zero_streak=2;updated=1747700000'

    def test_parse__extracts_fields(self):
        record = self.builder.parse('zero_streak=2;updated=1747700000')
        assert int(record.zero_streak) == 2
        assert int(record.updated)     == 1747700000

    def test_parse__rejects_missing_field(self):
        with self.assertRaises(ValueError):
            self.builder.parse('zero_streak=2')                                  # no updated

    def test_parse__rejects_malformed_segment(self):
        with self.assertRaises(ValueError):
            self.builder.parse('zero_streak;updated=1747700000')

    def test_round_trip(self):
        record   = Schema__SG_Edge__State__Record(zero_streak=5, updated=1747700123)
        reparsed = self.builder.parse(self.builder.build(record))
        assert self.builder.build(reparsed) == self.builder.build(record)

    def test_try_parse__returns_none_on_bad_input(self):
        assert self.builder.try_parse('garbage') is None
        assert self.builder.try_parse('')        is None
