# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__AWS__Client
# Composition shell: tag constants, FIREFOX_NAMING, and helper slots.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.service.Firefox__IAM__Helper                         import Firefox__IAM__Helper
from sg_compute_specs.firefox.service.Firefox__Instance__Helper                    import Firefox__Instance__Helper
from sg_compute_specs.firefox.service.Firefox__Launch__Helper                      import Firefox__Launch__Helper
from sg_compute_specs.firefox.service.Firefox__SG__Helper                          import Firefox__SG__Helper
from sg_compute_specs.firefox.service.Firefox__Tags__Builder                       import Firefox__Tags__Builder
from sg_compute_specs.firefox.service.Firefox__Tags                                import (FIREFOX_NAMING      ,
                                                                                            TAG_ALLOWED_IP_KEY  ,
                                                                                            TAG_CREATOR_KEY     ,
                                                                                            TAG_PURPOSE_KEY     ,
                                                                                            TAG_PURPOSE_VALUE   ,
                                                                                            TAG_SECTION_KEY     ,
                                                                                            TAG_SECTION_VALUE   ,
                                                                                            TAG_STACK_NAME_KEY  )


class Firefox__AWS__Client(Type_Safe):
    sg       : Optional[Firefox__SG__Helper]       = None
    instance : Optional[Firefox__Instance__Helper] = None
    tags     : Optional[Firefox__Tags__Builder]    = None
    launch   : Optional[Firefox__Launch__Helper]   = None
    iam      : Optional[Firefox__IAM__Helper]      = None

    def setup(self) -> 'Firefox__AWS__Client':
        self.sg       = Firefox__SG__Helper      ()
        self.instance = Firefox__Instance__Helper()
        self.launch   = Firefox__Launch__Helper  ()
        self.tags     = Firefox__Tags__Builder   ()
        self.iam      = Firefox__IAM__Helper     ()
        return self
