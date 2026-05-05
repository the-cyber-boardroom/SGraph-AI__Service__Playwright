# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.neko.service.Neko__AMI__Helper                               import Neko__AMI__Helper
from sg_compute_specs.neko.service.Neko__Instance__Helper                          import Neko__Instance__Helper
from sg_compute_specs.neko.service.Neko__Launch__Helper                            import Neko__Launch__Helper
from sg_compute_specs.neko.service.Neko__SG__Helper                                import Neko__SG__Helper
from sg_compute_specs.neko.service.Neko__Tags__Builder                             import Neko__Tags__Builder
from sg_compute_specs.neko.service.Neko__Tags                                      import (NEKO_NAMING         ,
                                                                                            TAG_ALLOWED_IP_KEY  ,
                                                                                            TAG_CREATOR_KEY     ,
                                                                                            TAG_PURPOSE_KEY     ,
                                                                                            TAG_PURPOSE_VALUE   ,
                                                                                            TAG_SECTION_KEY     ,
                                                                                            TAG_SECTION_VALUE   ,
                                                                                            TAG_STACK_NAME_KEY  )


class Neko__AWS__Client(Type_Safe):
    sg       : Optional[Neko__SG__Helper]       = None
    ami      : Optional[Neko__AMI__Helper]      = None
    instance : Optional[Neko__Instance__Helper] = None
    tags     : Optional[Neko__Tags__Builder]    = None
    launch   : Optional[Neko__Launch__Helper]   = None

    def setup(self) -> 'Neko__AWS__Client':
        self.sg       = Neko__SG__Helper      ()
        self.ami      = Neko__AMI__Helper     ()
        self.instance = Neko__Instance__Helper()
        self.tags     = Neko__Tags__Builder   ()
        self.launch   = Neko__Launch__Helper  ()
        return self
