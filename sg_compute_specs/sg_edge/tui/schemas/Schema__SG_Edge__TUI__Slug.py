# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Schema__SG_Edge__TUI__Slug
# A slug as the TUI renders it: name, fqdn, derived state, and backend pointer.
# Source-independent (local or AWS produce the same shape). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State      import Enum__SG_Edge__TUI__Slug_State


class Schema__SG_Edge__TUI__Slug(Type_Safe):
    slug         : str
    fqdn         : str
    state        : Enum__SG_Edge__TUI__Slug_State = Enum__SG_Edge__TUI__Slug_State.DORMANT
    backend_ip   : str
    backend_port : int = 0
