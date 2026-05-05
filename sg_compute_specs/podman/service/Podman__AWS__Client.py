# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Podman__AWS__Client
# Composition shell for per-concern AWS helpers.
#
# Tag convention:
#   sg:purpose    : podman
#   sg:stack-name : {stack_name}
#   sg:allowed-ip : {caller_ip}
#   sg:creator    : git email or $USER
#   sg:section    : podman
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.podman.service.Podman__AMI__Helper                           import Podman__AMI__Helper
from sg_compute_specs.podman.service.Podman__Instance__Helper                      import Podman__Instance__Helper
from sg_compute_specs.podman.service.Podman__Launch__Helper                        import Podman__Launch__Helper
from sg_compute_specs.podman.service.Podman__SG__Helper                            import Podman__SG__Helper
from sg_compute_specs.podman.service.Podman__Tags__Builder                         import Podman__Tags__Builder
from sg_compute_specs.podman.service.Podman__Tags                                  import (PODMAN_NAMING      ,
                                                                                            TAG_ALLOWED_IP_KEY ,
                                                                                            TAG_CREATOR_KEY    ,
                                                                                            TAG_PURPOSE_KEY    ,
                                                                                            TAG_PURPOSE_VALUE  ,
                                                                                            TAG_SECTION_KEY    ,
                                                                                            TAG_SECTION_VALUE  ,
                                                                                            TAG_STACK_NAME_KEY )


class Podman__AWS__Client(Type_Safe):
    sg       : Optional[Podman__SG__Helper]       = None
    ami      : Optional[Podman__AMI__Helper]      = None
    instance : Optional[Podman__Instance__Helper] = None
    tags     : Optional[Podman__Tags__Builder]    = None
    launch   : Optional[Podman__Launch__Helper]   = None

    def setup(self) -> 'Podman__AWS__Client':
        self.sg       = Podman__SG__Helper      ()
        self.ami      = Podman__AMI__Helper     ()
        self.instance = Podman__Instance__Helper()
        self.tags     = Podman__Tags__Builder   ()
        self.launch   = Podman__Launch__Helper  ()
        return self
