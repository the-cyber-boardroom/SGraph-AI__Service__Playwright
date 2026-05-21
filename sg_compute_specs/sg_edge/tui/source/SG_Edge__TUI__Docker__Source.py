# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Docker__Source
# "What is running on the local Docker right now?" — a thin read-only seam over the
# existing host-plane `Pod__Runtime` (which shells out to the `docker` CLI; no SDK).
# `runtime` is injected: the CLI passes `Pod__Runtime__Docker`; tests pass a fake
# `Pod__Runtime` subclass with a canned `list()` (no mocks, no daemon needed). A
# missing/unreachable daemon is swallowed → empty list (`available()` is False), so
# the screen renders an honest "docker not reachable" rather than crashing.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute.host_plane.pods.service.Pod__Runtime                        import Pod__Runtime
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List


class SG_Edge__TUI__Docker__Source(Type_Safe):
    runtime : Pod__Runtime                                                           # inject Pod__Runtime__Docker (CLI) or a fake subclass (tests)

    def containers(self) -> Schema__Pod__List:
        try:
            return self.runtime.list()
        except Exception:                                                            # daemon down / docker absent → honest empty
            return Schema__Pod__List()

    def available(self) -> bool:
        try:
            self.runtime.list()
            return True
        except Exception:
            return False
