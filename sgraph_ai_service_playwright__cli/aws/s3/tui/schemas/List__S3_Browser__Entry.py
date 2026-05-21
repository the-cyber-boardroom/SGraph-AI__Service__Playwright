# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: List__S3_Browser__Entry
# Typed list of Schema__S3_Browser__Entry. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.s3.tui.schemas.Schema__S3_Browser__Entry import Schema__S3_Browser__Entry


class List__S3_Browser__Entry(Type_Safe__List):
    expected_type = Schema__S3_Browser__Entry
