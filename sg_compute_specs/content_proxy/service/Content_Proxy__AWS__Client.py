# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__AWS__Client
# Composes the shared EC2 helpers — the SAME foundation `sg va create` uses.
# No new AWS logic; just binds the content_proxy naming + stack-type.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__AMI__Helper                              import EC2__AMI__Helper
from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper                         import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__Launch__Helper                           import EC2__Launch__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper                               import EC2__SG__Helper
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder                            import EC2__Tags__Builder
from sg_compute.platforms.ec2.helpers.Stack__Naming                                 import Stack__Naming


STACK_TYPE = 'content-proxy'
CP_NAMING  = Stack__Naming(section_prefix='cp')                                     # AWS Name / SG: cp-<stack>


class Content_Proxy__AWS__Client(Type_Safe):
    sg       : Optional[EC2__SG__Helper]       = None
    ami      : Optional[EC2__AMI__Helper]      = None
    instance : Optional[EC2__Instance__Helper] = None
    tags     : Optional[EC2__Tags__Builder]    = None
    launch   : Optional[EC2__Launch__Helper]   = None

    def setup(self) -> 'Content_Proxy__AWS__Client':
        self.sg       = EC2__SG__Helper      ().setup(CP_NAMING)
        self.ami      = EC2__AMI__Helper      ()
        self.instance = EC2__Instance__Helper ()
        self.tags     = EC2__Tags__Builder    (stack_type=STACK_TYPE)
        self.launch   = EC2__Launch__Helper   ()
        return self
