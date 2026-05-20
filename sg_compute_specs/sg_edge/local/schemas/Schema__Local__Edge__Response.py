# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Schema__Local__Edge__Response
# The result of one simulated request through the local edge (proxy output).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Response_Kind          import Enum__Local__Edge__Response_Kind


class Schema__Local__Edge__Response(Type_Safe):
    slug        : str
    host        : str
    status_code : int                              = 200
    kind        : Enum__Local__Edge__Response_Kind = Enum__Local__Edge__Response_Kind.WELCOME
    title       : str                                                                # short human title (e.g. "Welcome to the alice vault")
    body        : str                                                                # full HTML body served to the client
    backend     : str                                                                # ip:port the request would proxy to (empty when none)
