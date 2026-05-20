# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Glyphs
# Status glyph + semantic colour for the screens — shared so the same state means
# the same thing everywhere (brief principle: colour is semantic, not decorative).
# Pure (no textual, no rich import) — returns (glyph, rich-style-name) pairs; the
# view layer embeds them as markup. Runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity      import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State      import Enum__SG_Edge__TUI__Slug_State

SLUG_GLYPH = {Enum__SG_Edge__TUI__Slug_State.LIVE          : ('●', 'green'),
              Enum__SG_Edge__TUI__Slug_State.DORMANT       : ('◐', 'yellow'),
              Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND: ('✗', 'red')}

SEVERITY_GLYPH = {Enum__Local__Edge__Severity.OK   : ('✓', 'green'),
                  Enum__Local__Edge__Severity.INFO : ('·', 'dim'),
                  Enum__Local__Edge__Severity.WARN : ('⚠', 'yellow'),
                  Enum__Local__Edge__Severity.ERROR: ('✗', 'red')}


def slug_glyph(state) -> tuple:
    return SLUG_GLYPH.get(state, ('·', 'white'))


def severity_glyph(severity) -> tuple:
    return SEVERITY_GLYPH.get(severity, ('·', 'white'))


def yes_no(flag : bool) -> tuple:                                                    # ✓ green / ✗ red for a boolean capability
    return ('✓', 'green') if flag else ('✗', 'red')
