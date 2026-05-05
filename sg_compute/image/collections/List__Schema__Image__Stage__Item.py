# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — List__Schema__Image__Stage__Item
# Ordered list of files/trees to stage into the Docker build context.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute.image.schemas.Schema__Image__Stage__Item                            import Schema__Image__Stage__Item


class List__Schema__Image__Stage__Item(Type_Safe__List):
    expected_type = Schema__Image__Stage__Item
