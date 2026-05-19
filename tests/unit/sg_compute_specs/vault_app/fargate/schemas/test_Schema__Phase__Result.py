# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Schema__Phase__Result
# Verifies default construction, field assignment, and schema completeness.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.schemas.Schema__Phase__Result  import Schema__Phase__Result


class test_Schema__Phase__Result(TestCase):

    def test_default_construction_has_expected_fields(self):            # all required fields present
        result = Schema__Phase__Result()
        assert hasattr(result, 'name')
        assert hasattr(result, 'status')
        assert hasattr(result, 'duration_ms')
        assert hasattr(result, 'started_at')
        assert hasattr(result, 'error')
        assert hasattr(result, 'detail')

    def test_default_field_values(self):                                # Type_Safe defaults match spec
        result = Schema__Phase__Result()
        assert result.name        == ''
        assert result.status      is None
        assert result.duration_ms == 0
        assert result.started_at  == ''
        assert result.error       == ''
        assert result.detail      == ''

    def test_fields_are_settable(self):                                 # fields accept assignment
        result = Schema__Phase__Result()
        result.name        = 'ecr'
        result.status      = Enum__VAF__Phase__Status.OK
        result.duration_ms = 1234
        result.started_at  = '2026-05-19T00:00:00+00:00'
        result.error       = ''
        result.detail      = 'repo exists'
        assert result.name        == 'ecr'
        assert result.status      == Enum__VAF__Phase__Status.OK
        assert result.duration_ms == 1234
        assert result.started_at  == '2026-05-19T00:00:00+00:00'
        assert result.error       == ''
        assert result.detail      == 'repo exists'

    def test_construction_with_kwargs(self):                            # keyword-arg construction matches spec
        result = Schema__Phase__Result(
            name       = 'iam',
            status     = Enum__VAF__Phase__Status.RUNNING,
            started_at = '2026-05-19T00:01:00+00:00',
        )
        assert result.name   == 'iam'
        assert result.status == Enum__VAF__Phase__Status.RUNNING
