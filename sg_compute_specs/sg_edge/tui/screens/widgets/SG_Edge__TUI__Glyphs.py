# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Glyphs
# Status glyph + semantic colour for the screens — shared so the same state means
# the same thing everywhere (brief principle: colour is semantic, not decorative).
# Pure (no textual, no rich import) — returns (glyph, rich-style-name) pairs; the
# view layer embeds them as markup. Runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity      import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind      import Enum__SG_Edge__TUI__Event_Kind
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State      import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Sync_State      import Enum__SG_Edge__TUI__Sync_State

SLUG_GLYPH = {Enum__SG_Edge__TUI__Slug_State.LIVE          : ('●', 'green'),
              Enum__SG_Edge__TUI__Slug_State.DORMANT       : ('◐', 'yellow'),
              Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND: ('✗', 'red')}

SEVERITY_GLYPH = {Enum__Local__Edge__Severity.OK   : ('✓', 'green'),
                  Enum__Local__Edge__Severity.INFO : ('·', 'dim'),
                  Enum__Local__Edge__Severity.WARN : ('⚠', 'yellow'),
                  Enum__Local__Edge__Severity.ERROR: ('✗', 'red')}

SYNC_GLYPH = {Enum__SG_Edge__TUI__Sync_State.IN_SYNC   : ('●', 'green'),
              Enum__SG_Edge__TUI__Sync_State.LOCAL_ONLY: ('⚠', 'yellow'),
              Enum__SG_Edge__TUI__Sync_State.EDGE_ONLY : ('⚠', 'yellow')}

EVENT_GLYPH = {Enum__SG_Edge__TUI__Event_Kind.SLUG_REGISTERED: ('+', 'green'),
               Enum__SG_Edge__TUI__Event_Kind.WENT_LIVE       : ('▲', 'green'),
               Enum__SG_Edge__TUI__Event_Kind.WENT_DORMANT    : ('▼', 'yellow'),
               Enum__SG_Edge__TUI__Event_Kind.REMOVED         : ('-', 'red'),
               Enum__SG_Edge__TUI__Event_Kind.FLEET_CHANGED   : ('≈', 'cyan'),
               Enum__SG_Edge__TUI__Event_Kind.ISSUE           : ('⚠', 'yellow'),
               Enum__SG_Edge__TUI__Event_Kind.CLEARED         : ('✓', 'green')}


def slug_glyph(state) -> tuple:
    return SLUG_GLYPH.get(state, ('·', 'white'))


def severity_glyph(severity) -> tuple:
    return SEVERITY_GLYPH.get(severity, ('·', 'white'))


def sync_glyph(state) -> tuple:
    return SYNC_GLYPH.get(state, ('·', 'white'))


def event_glyph(kind) -> tuple:
    return EVENT_GLYPH.get(kind, ('·', 'white'))


def yes_no(flag : bool) -> tuple:                                                    # ✓ green / ✗ red for a boolean capability
    return ('✓', 'green') if flag else ('✗', 'red')
