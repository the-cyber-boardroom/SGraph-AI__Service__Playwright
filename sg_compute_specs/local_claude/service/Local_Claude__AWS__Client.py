# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Local_Claude__AWS__Client
# Composition shell wiring the per-concern AWS helpers for the local-claude stack.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional
from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__AMI__Helper      import EC2__AMI__Helper
from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__Launch__Helper   import EC2__Launch__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper       import EC2__SG__Helper
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder    import EC2__Tags__Builder
from sg_compute.platforms.ec2.helpers.Stack__Naming         import Stack__Naming

from sg_compute_specs.local_claude.service.Local_Claude__Stack__Mapper import STACK_TYPE

LC_NAMING = Stack__Naming(section_prefix='lc')


class Local_Claude__AWS__Client(Type_Safe):
    sg       : Optional[EC2__SG__Helper]       = None
    ami      : Optional[EC2__AMI__Helper]      = None
    instance : Optional[EC2__Instance__Helper] = None
    tags     : Optional[EC2__Tags__Builder]    = None
    launch   : Optional[EC2__Launch__Helper]   = None

    def setup(self) -> 'Local_Claude__AWS__Client':
        self.sg       = EC2__SG__Helper      ().setup(LC_NAMING)
        self.ami      = EC2__AMI__Helper      ()
        self.instance = EC2__Instance__Helper ()
        self.tags     = EC2__Tags__Builder    (stack_type=STACK_TYPE)
        self.launch   = EC2__Launch__Helper   ()
        return self
