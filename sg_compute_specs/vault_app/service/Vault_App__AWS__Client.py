# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__AWS__Client
# Composition shell wiring the per-concern AWS helpers for the vault-app stack.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

import boto3                                                                   # EXCEPTION — narrow boto3 boundary (STS account lookup)

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__AMI__Helper      import EC2__AMI__Helper
from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__Launch__Helper   import EC2__Launch__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper       import EC2__SG__Helper
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder    import EC2__Tags__Builder
from sg_compute.platforms.ec2.helpers.Stack__Naming         import Stack__Naming

from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper import STACK_TYPE

VA_NAMING = Stack__Naming(section_prefix='va')


def ecr_registry_host(region: str) -> str:                                     # <account>.dkr.ecr.<region>.amazonaws.com
    account = boto3.client('sts', region_name=region).get_caller_identity()['Account']
    return f'{account}.dkr.ecr.{region}.amazonaws.com'


class Vault_App__AWS__Client(Type_Safe):
    sg       : Optional[EC2__SG__Helper]       = None
    ami      : Optional[EC2__AMI__Helper]      = None
    instance : Optional[EC2__Instance__Helper] = None
    tags     : Optional[EC2__Tags__Builder]    = None
    launch   : Optional[EC2__Launch__Helper]   = None

    def setup(self) -> 'Vault_App__AWS__Client':
        self.sg       = EC2__SG__Helper      ().setup(VA_NAMING)
        self.ami      = EC2__AMI__Helper      ()
        self.instance = EC2__Instance__Helper ()
        self.tags     = EC2__Tags__Builder    (stack_type=STACK_TYPE)
        self.launch   = EC2__Launch__Helper   ()
        return self
