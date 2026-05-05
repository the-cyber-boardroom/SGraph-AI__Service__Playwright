# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__AWS__Client
# Composition shell for per-concern AWS helpers.
#
# Tag convention:
#   sg:purpose     : vnc
#   sg:stack-name  : {stack_name}
#   sg:allowed-ip  : {caller_ip}
#   sg:creator     : git email or $USER
#   sg:section     : vnc
#   sg:interceptor : <name | inline | none>
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.vnc.service.Vnc__AMI__Helper                                 import Vnc__AMI__Helper
from sg_compute_specs.vnc.service.Vnc__Instance__Helper                            import Vnc__Instance__Helper
from sg_compute_specs.vnc.service.Vnc__Launch__Helper                              import Vnc__Launch__Helper
from sg_compute_specs.vnc.service.Vnc__SG__Helper                                  import Vnc__SG__Helper
from sg_compute_specs.vnc.service.Vnc__Tags__Builder                               import Vnc__Tags__Builder
from sg_compute_specs.vnc.service.Vnc__Tags                                        import (VNC_NAMING           ,
                                                                                            TAG_ALLOWED_IP_KEY   ,
                                                                                            TAG_CREATOR_KEY      ,
                                                                                            TAG_INTERCEPTOR_KEY  ,
                                                                                            TAG_INTERCEPTOR_NONE ,
                                                                                            TAG_PURPOSE_KEY      ,
                                                                                            TAG_PURPOSE_VALUE    ,
                                                                                            TAG_SECTION_KEY      ,
                                                                                            TAG_SECTION_VALUE    ,
                                                                                            TAG_STACK_NAME_KEY   )


class Vnc__AWS__Client(Type_Safe):
    sg       : Optional[Vnc__SG__Helper]       = None
    ami      : Optional[Vnc__AMI__Helper]      = None
    instance : Optional[Vnc__Instance__Helper] = None
    tags     : Optional[Vnc__Tags__Builder]    = None
    launch   : Optional[Vnc__Launch__Helper]   = None

    def setup(self) -> 'Vnc__AWS__Client':
        self.sg       = Vnc__SG__Helper      ()
        self.ami      = Vnc__AMI__Helper     ()
        self.instance = Vnc__Instance__Helper()
        self.tags     = Vnc__Tags__Builder   ()
        self.launch   = Vnc__Launch__Helper  ()
        return self
