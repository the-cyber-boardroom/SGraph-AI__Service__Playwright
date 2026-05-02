# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Request__Validator (cross-field rules for stack-creation requests)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Creation_Mode       import Enum__Stack__Creation_Mode
from sgraph_ai_service_playwright__cli.catalog.primitives.Safe_Str__AWS__AMI_Id       import Safe_Str__AWS__AMI_Id
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Create__Request__Base import Schema__Stack__Create__Request__Base
from sgraph_ai_service_playwright__cli.catalog.service.Request__Validator              import Request__Validator


def _req(**kwargs) -> Schema__Stack__Create__Request__Base:
    return Schema__Stack__Create__Request__Base(**kwargs)


class test_Request__Validator(TestCase):

    def setUp(self):
        self.validator = Request__Validator()

    # ── FRESH mode ───────────────────────────────────────────────────────────

    def test_fresh_mode__no_ami__valid(self):
        ok, err = self.validator.validate_create(_req(creation_mode=Enum__Stack__Creation_Mode.FRESH))
        assert ok  is True
        assert err is None

    def test_fresh_mode__with_ami__invalid(self):
        ok, err = self.validator.validate_create(
            _req(creation_mode = Enum__Stack__Creation_Mode.FRESH            ,
                 ami_id        = Safe_Str__AWS__AMI_Id('ami-0123456789abcdef0')))
        assert ok  is False
        assert 'must be absent' in err

    # ── BAKE_AMI mode ────────────────────────────────────────────────────────

    def test_bake_ami_mode__no_ami__valid(self):
        ok, err = self.validator.validate_create(_req(creation_mode=Enum__Stack__Creation_Mode.BAKE_AMI))
        assert ok  is True
        assert err is None

    def test_bake_ami_mode__with_ami__invalid(self):
        ok, err = self.validator.validate_create(
            _req(creation_mode = Enum__Stack__Creation_Mode.BAKE_AMI         ,
                 ami_id        = Safe_Str__AWS__AMI_Id('ami-0123456789abcdef0')))
        assert ok  is False
        assert 'must be absent' in err

    # ── FROM_AMI mode ────────────────────────────────────────────────────────

    def test_from_ami_mode__with_valid_ami__valid(self):
        ok, err = self.validator.validate_create(
            _req(creation_mode = Enum__Stack__Creation_Mode.FROM_AMI          ,
                 ami_id        = Safe_Str__AWS__AMI_Id('ami-0123456789abcdef0')))
        assert ok  is True
        assert err is None

    def test_from_ami_mode__no_ami__invalid(self):
        ok, err = self.validator.validate_create(
            _req(creation_mode=Enum__Stack__Creation_Mode.FROM_AMI))
        assert ok  is False
        assert 'ami_id is required' in err

    def test_from_ami_mode__bad_ami_prefix__invalid(self):
        ok, err = self.validator.validate_create(
            _req(creation_mode = Enum__Stack__Creation_Mode.FROM_AMI ,
                 ami_id        = Safe_Str__AWS__AMI_Id('snap-00000000')))
        assert ok  is False
        assert 'must start with "ami-"' in err

    # ── Schema defaults ──────────────────────────────────────────────────────

    def test_schema_default_creation_mode_is_fresh(self):
        req = Schema__Stack__Create__Request__Base()
        assert req.creation_mode == Enum__Stack__Creation_Mode.FRESH

    def test_schema_default_instance_size_is_medium(self):
        from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Instance__Size import Enum__Instance__Size
        req = Schema__Stack__Create__Request__Base()
        assert req.instance_size == Enum__Instance__Size.MEDIUM

    def test_schema_timeout_default_is_zero(self):
        req = Schema__Stack__Create__Request__Base()
        assert int(req.timeout_minutes) == 0
