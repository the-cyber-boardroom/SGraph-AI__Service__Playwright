# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Firefox__AMI__Info
# Ordered list of Firefox AMI records. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__AMI__Info   import Schema__Firefox__AMI__Info


class List__Schema__Firefox__AMI__Info(Type_Safe__List):
    expected_type = Schema__Firefox__AMI__Info
