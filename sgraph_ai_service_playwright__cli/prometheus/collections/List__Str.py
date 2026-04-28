# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Str (prometheus-local copy)
# Typed list of plain strings used by the scrape-target schema for the
# `static_configs.targets` host:port list. Sister sections stay self-
# contained; promotion to a shared cli/aws/ location is a future cleanup.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List


class List__Str(Type_Safe__List):
    expected_type = str
