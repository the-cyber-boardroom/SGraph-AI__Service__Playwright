# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: sg_edge_tui__config
# Shared constants for the SG/Edge TUI (the data layer + the eventual screens).
#
# Refresh is deliberately slow: the data is DNS-grounded operational state, and
# every redraw is bytes over the SSH/SSM chain (framing-brief addendum). 2 s is
# plenty; screens may override but should stay within 5–10 Hz at most.
#
# REAL_CAPABILITIES names the panes that have real data today. Cost / throughput /
# instance panes are deliberately absent — they light up when v0.2.37 Slice 5
# (live EC2) and the observability event source land. No fabricated numbers.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target     import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Capability import Enum__SG_Edge__TUI__Capability

TUI_REFRESH_SECONDS   = 2.0                                                          # poll cadence; calmer than 60 FPS, kinder to flaky links
TUI_DEFAULT_TARGET    = Enum__SG_Edge__TUI__Target.LOCAL                              # default data source for `sg edge tui *`
TUI_DEFAULT_THEME     = 'dark'                                                        # dark default; light is a `t` toggle in the screens
TUI_SERIES_MAX_POINTS = 60                                                            # sparkline ring-buffer length (per metric)
TUI_CARD_WIDTH        = 64                                                            # ASCII export card inner width

REAL_CAPABILITIES = (Enum__SG_Edge__TUI__Capability.TOPOLOGY,                         # panes backed by real data today
                     Enum__SG_Edge__TUI__Capability.SLUGS,
                     Enum__SG_Edge__TUI__Capability.CHECKS,
                     Enum__SG_Edge__TUI__Capability.FLEET)
