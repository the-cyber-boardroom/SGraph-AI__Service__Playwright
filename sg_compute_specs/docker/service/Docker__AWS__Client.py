# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__AWS__Client
# Composition shell for per-concern AWS helpers.
#
# Tag convention:
#   sg:purpose    : docker
#   sg:stack-name : {stack_name}
#   sg:allowed-ip : {caller_ip}
#   sg:creator    : git email or $USER
#   sg:section    : docker
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.docker.service.Docker__AMI__Helper                           import Docker__AMI__Helper
from sg_compute_specs.docker.service.Docker__Instance__Helper                      import Docker__Instance__Helper
from sg_compute_specs.docker.service.Docker__Launch__Helper                        import Docker__Launch__Helper
from sg_compute_specs.docker.service.Docker__SG__Helper                            import Docker__SG__Helper
from sg_compute_specs.docker.service.Docker__Tags__Builder                         import Docker__Tags__Builder
from sg_compute_specs.docker.service.Docker__Tags                                  import (DOCKER_NAMING      ,
                                                                                            TAG_ALLOWED_IP_KEY  ,
                                                                                            TAG_CREATOR_KEY     ,
                                                                                            TAG_PURPOSE_KEY     ,
                                                                                            TAG_PURPOSE_VALUE   ,
                                                                                            TAG_SECTION_KEY     ,
                                                                                            TAG_SECTION_VALUE   ,
                                                                                            TAG_STACK_NAME_KEY  )


class Docker__AWS__Client(Type_Safe):
    sg       : Optional[Docker__SG__Helper]       = None
    ami      : Optional[Docker__AMI__Helper]      = None
    instance : Optional[Docker__Instance__Helper] = None
    tags     : Optional[Docker__Tags__Builder]    = None
    launch   : Optional[Docker__Launch__Helper]   = None

    def setup(self) -> 'Docker__AWS__Client':
        self.sg       = Docker__SG__Helper      ()
        self.ami      = Docker__AMI__Helper     ()
        self.instance = Docker__Instance__Helper()
        self.tags     = Docker__Tags__Builder   ()
        self.launch   = Docker__Launch__Helper  ()
        return self
