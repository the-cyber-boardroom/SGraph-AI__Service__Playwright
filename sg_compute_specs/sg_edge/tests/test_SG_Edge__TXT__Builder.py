# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for SG_Edge__TXT__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.enums.Enum__SG_Edge__Backend__Type    import Enum__SG_Edge__Backend__Type
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__TXT__Record  import Schema__SG_Edge__TXT__Record
from sg_compute_specs.sg_edge.service.SG_Edge__TXT__Builder         import SG_Edge__TXT__Builder, MAX_TXT_LENGTH


class test_SG_Edge__TXT__Builder(TestCase):

    def setUp(self):
        self.builder = SG_Edge__TXT__Builder()

    def _record(self, **kw):
        defaults = dict(ip       = '10.0.1.5'                         ,
                        port     = 8080                               ,
                        type     = Enum__SG_Edge__Backend__Type.EC2   ,
                        launched = 1747700000                         )
        defaults.update(kw)
        return Schema__SG_Edge__TXT__Record(**defaults)

    # ── build ───────────────────────────────────────────────────────────────

    def test_build__emits_canonical_order(self):
        txt = self.builder.build(self._record())
        assert txt == 'v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000'

    def test_build__includes_instance_when_set(self):
        txt = self.builder.build(self._record(instance='i-0abc123def4567890'))
        assert txt == 'v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000;instance=i-0abc123def4567890'

    def test_build__omits_instance_when_unset(self):
        assert 'instance=' not in self.builder.build(self._record())

    def test_build__fargate_type(self):
        txt = self.builder.build(self._record(type=Enum__SG_Edge__Backend__Type.FARGATE))
        assert 'type=fargate' in txt

    def test_build__under_dns_limit(self):
        assert len(self.builder.build(self._record(instance='i-0abc123def4567890'))) <= MAX_TXT_LENGTH

    # ── parse ───────────────────────────────────────────────────────────────

    def test_parse__extracts_all_fields(self):
        record = self.builder.parse('v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000;instance=i-0abc123def4567890')
        assert int(record.version)  == 1
        assert str(record.ip)       == '10.0.1.5'
        assert int(record.port)     == 8080
        assert record.type          == Enum__SG_Edge__Backend__Type.EC2
        assert int(record.launched) == 1747700000
        assert str(record.instance) == 'i-0abc123def4567890'

    def test_parse__instance_optional(self):
        record = self.builder.parse('v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000')
        assert str(record.instance) == ''

    def test_parse__tolerates_whitespace_and_trailing_separator(self):
        record = self.builder.parse(' v=1 ; ip=10.0.1.5 ; port=8080 ; type=ec2 ; launched=1747700000 ; ')
        assert str(record.ip) == '10.0.1.5'

    def test_parse__rejects_unsupported_version(self):
        with self.assertRaises(ValueError):
            self.builder.parse('v=2;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000')

    def test_parse__rejects_missing_required_field(self):
        with self.assertRaises(ValueError):
            self.builder.parse('v=1;ip=10.0.1.5;type=ec2;launched=1747700000')          # no port

    def test_parse__rejects_malformed_segment(self):
        with self.assertRaises(ValueError):
            self.builder.parse('v=1;ip=10.0.1.5;port;type=ec2;launched=1747700000')     # `port` has no value

    def test_parse__rejects_unknown_backend_type(self):
        with self.assertRaises(ValueError):
            self.builder.parse('v=1;ip=10.0.1.5;port=8080;type=k8s;launched=1747700000')

    # ── round-trip ─────────────────────────────────────────────────────────────

    def test_round_trip__build_then_parse(self):
        original = self._record(instance='i-0abc123def4567890')
        reparsed = self.builder.parse(self.builder.build(original))
        assert self.builder.build(reparsed) == self.builder.build(original)

    # ── try_parse / is_valid ─────────────────────────────────────────────────────

    def test_try_parse__returns_none_on_bad_input(self):
        assert self.builder.try_parse('not a txt record') is None
        assert self.builder.try_parse('v=9;ip=10.0.1.5;port=8080;type=ec2;launched=1') is None

    def test_try_parse__returns_record_on_good_input(self):
        assert self.builder.try_parse('v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000') is not None

    def test_is_valid(self):
        assert self.builder.is_valid('v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000') is True
        assert self.builder.is_valid('garbage')                                          is False
        assert self.builder.is_valid('')                                                 is False
