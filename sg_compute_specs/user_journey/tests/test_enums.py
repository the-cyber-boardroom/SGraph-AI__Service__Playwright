# ═══════════════════════════════════════════════════════════════════════════════
# Tests — User-Journey enums
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status     import Enum__Assertion__Status
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type       import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Journey__Run__Status  import Enum__Journey__Run__Status


class TestUserJourneyEnums:

    def test_assertion_type_values(self):
        assert Enum__Assertion__Type('url_contains') is Enum__Assertion__Type.URL_CONTAINS
        assert str(Enum__Assertion__Type.HTTP_HEADER_PRESENT) == 'http_header_present'
        assert len(list(Enum__Assertion__Type)) == 7

    def test_assertion_status_values(self):
        assert {s.value for s in Enum__Assertion__Status} == {'passed', 'failed', 'error', 'skipped'}

    def test_run_status_values(self):
        assert {s.value for s in Enum__Journey__Run__Status} == {'passed', 'failed', 'error'}
