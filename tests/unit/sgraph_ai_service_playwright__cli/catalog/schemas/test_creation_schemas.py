# ═══════════════════════════════════════════════════════════════════════════════
# Tests — stack-creation schemas (Item 2)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__AMI__Bake__State    import Enum__AMI__Bake__State
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Instance__Size      import Enum__Instance__Size
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Creation_Mode import Enum__Stack__Creation_Mode
from sgraph_ai_service_playwright__cli.catalog.primitives.Safe_Int__Timeout__Minutes import Safe_Int__Timeout__Minutes
from sgraph_ai_service_playwright__cli.catalog.primitives.Safe_Str__AWS__AMI_Id import Safe_Str__AWS__AMI_Id
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__AMI__Bake__Status import Schema__AMI__Bake__Status
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Create__Request__Base import Schema__Stack__Create__Request__Base
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime import Safe_Str__ISO_Datetime


class test_creation_schemas(TestCase):

    # ── Enum__Stack__Creation_Mode ────────────────────────────────────────────

    def test_creation_mode__values(self):
        assert Enum__Stack__Creation_Mode.FRESH.value    == 'fresh'
        assert Enum__Stack__Creation_Mode.BAKE_AMI.value == 'bake-ami'
        assert Enum__Stack__Creation_Mode.FROM_AMI.value == 'from-ami'

    # ── Enum__Instance__Size ──────────────────────────────────────────────────

    def test_instance_size__values(self):
        assert Enum__Instance__Size.SMALL.value  == 'small'
        assert Enum__Instance__Size.MEDIUM.value == 'medium'
        assert Enum__Instance__Size.LARGE.value  == 'large'

    # ── Safe_Str__AWS__AMI_Id ────────────────────────────────────────────────

    def test_ami_id__accepts_valid(self):
        assert str(Safe_Str__AWS__AMI_Id('ami-0123456789abcdef0')) == 'ami-0123456789abcdef0'

    def test_ami_id__strips_uppercase(self):
        val = str(Safe_Str__AWS__AMI_Id('AMI-ABC'))
        assert 'A' not in val and 'M' not in val and 'I' not in val

    def test_ami_id__empty_allowed(self):
        assert str(Safe_Str__AWS__AMI_Id()) == ''

    # ── Safe_Int__Timeout__Minutes ────────────────────────────────────────────

    def test_timeout_minutes__zero_default(self):
        assert int(Safe_Int__Timeout__Minutes()) == 0

    def test_timeout_minutes__accepts_positive(self):
        assert int(Safe_Int__Timeout__Minutes(60)) == 60

    def test_timeout_minutes__rejects_over_cap(self):
        import pytest
        with pytest.raises(ValueError):
            Safe_Int__Timeout__Minutes(1441)

    # ── Schema__Stack__Create__Request__Base ─────────────────────────────────

    def test_base_schema__defaults(self):
        req = Schema__Stack__Create__Request__Base()
        assert req.creation_mode  == Enum__Stack__Creation_Mode.FRESH
        assert req.instance_size  == Enum__Instance__Size.MEDIUM
        assert int(req.timeout_minutes) == 0
        assert str(req.ami_id)    == ''

    def test_base_schema__json(self):
        req  = Schema__Stack__Create__Request__Base()
        data = req.json()
        assert data['creation_mode']   == 'fresh'
        assert data['instance_size']   == 'medium'
        assert data['timeout_minutes'] == 0

    # ── Schema__AMI__Bake__Status ─────────────────────────────────────────────

    def test_bake_status__default_state(self):
        s = Schema__AMI__Bake__Status()
        assert s.state == Enum__AMI__Bake__State.BAKING

    def test_bake_status__ready_with_ami(self):
        s = Schema__AMI__Bake__Status(
            state         = Enum__AMI__Bake__State.READY                   ,
            target_ami_id = Safe_Str__AWS__AMI_Id('ami-0deadbeef00000000') ,
            started_at    = Safe_Str__ISO_Datetime('2026-05-02T10:00:00Z') )
        assert s.state           == Enum__AMI__Bake__State.READY
        assert str(s.target_ami_id) == 'ami-0deadbeef00000000'
