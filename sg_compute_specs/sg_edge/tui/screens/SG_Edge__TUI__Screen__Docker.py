# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Docker
# "Local Docker" screen — what containers are running on the operator's machine.
# Thin view over SG_Edge__TUI__Docker__Source (which shells out to `docker ps`).
# r refresh / q quit (+ the shared ? / t from the base). Export (`e`) is a no-op
# here — there is no DNS snapshot to card.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Docker__Render              import docker_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS


class SG_Edge__TUI__Screen__Docker(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge Local Docker'
    BINDINGS = [('r', 'refresh', 'Refresh')]

    def __init__(self, docker_source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.docker_source   = docker_source
        self.refresh_seconds = refresh_seconds
        self.containers      = None
        self.available       = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_containers()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.refresh_containers)

    def refresh_containers(self) -> None:
        self.containers = self.docker_source.containers()
        self.available  = self.docker_source.available()
        self.query_one('#body', Static).update(docker_markup(self.containers, self.available))

    def action_refresh(self) -> None:
        self.refresh_containers()
