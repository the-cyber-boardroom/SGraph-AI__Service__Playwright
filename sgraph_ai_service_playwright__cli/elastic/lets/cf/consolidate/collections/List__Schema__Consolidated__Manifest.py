# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Consolidated__Manifest
# Typed list of consolidated-run manifests.  One per load() run.
# Bulk-posted to sg-cf-consolidated-{YYYY-MM-DD} with _id = run_id.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidated__Manifest import Schema__Consolidated__Manifest


class List__Schema__Consolidated__Manifest(Type_Safe__List):
    expected_type = Schema__Consolidated__Manifest
