# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__S3__Object__Record
# Ordered list of LETS-inventory records produced by S3__Inventory__Lister
# and consumed by Inventory__Loader.bulk_post(). Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record import Schema__S3__Object__Record


class List__Schema__S3__Object__Record(Type_Safe__List):
    expected_type = Schema__S3__Object__Record
