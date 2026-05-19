# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — List__Schema__Phase__Result
# Typed list of phase result schemas. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.vault_app.fargate.schemas.Schema__Phase__Result import Schema__Phase__Result


class List__Schema__Phase__Result(Type_Safe__List):
    expected_type = Schema__Phase__Result
