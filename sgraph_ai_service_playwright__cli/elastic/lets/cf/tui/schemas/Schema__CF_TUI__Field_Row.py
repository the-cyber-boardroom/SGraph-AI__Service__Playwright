# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Field_Row
# One field as the lineage inspector shows it: the group it belongs to (RAW / DERIVED
# / LINEAGE / PIPELINE), its name, the raw TSV value (RAW group only), the
# transformed/typed value, and whether the transform changed it. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Field_Row(Type_Safe):
    group   : str                                                                    # RAW / DERIVED / LINEAGE / PIPELINE
    name    : str
    raw     : str                                                                    # the raw TSV column (RAW group); '' for derived/lineage/pipeline
    value   : str                                                                    # the transformed / typed value
    changed : bool = False                                                           # RAW group: did the transform change the value?
