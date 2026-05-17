# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — List__Schema__Creds__Scope
# Typed list of scope catalogue entries.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.creds.schemas.Schema__Creds__Scope import Schema__Creds__Scope


class List__Schema__Creds__Scope(Type_Safe__List):
    expected_type = Schema__Creds__Scope
