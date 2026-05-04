# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Prom__Scrape__Target
# Ordered list of scrape jobs baked into prometheus.yml. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target


class List__Schema__Prom__Scrape__Target(Type_Safe__List):
    expected_type = Schema__Prom__Scrape__Target
