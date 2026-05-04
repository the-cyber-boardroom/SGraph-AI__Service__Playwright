# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Saved_Object__Type
# Subset of Kibana saved-object types we expose through `sp elastic dashboard`
# and `sp elastic data-view`. Kibana itself supports many more (lens, search,
# tag, map, …) but this CLI deliberately scopes to the two the user asked for:
#
#   DASHBOARD  — `dashboard` saved object (the visualisation board itself)
#   DATA_VIEW  — `index-pattern` saved object (renamed "data view" in Kibana
#                8.x UI but the API type string is still `index-pattern`)
#
# When exporting a dashboard with includeReferencesDeep=true, Kibana pulls in
# its referenced lens/visualization/search/data-view objects automatically —
# so the user gets a self-contained ndjson without listing those types here.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Saved_Object__Type(str, Enum):
    DASHBOARD = 'dashboard'
    DATA_VIEW = 'index-pattern'                                                     # Kibana 8.x renamed the UI label to "data view" but the API type is unchanged

    def __str__(self):
        return self.value
