# ═══════════════════════════════════════════════════════════════════════════════
# Tests — EC2 Schemas
# Tests for Schema__EC2__Instance, Schema__EC2__Instance__Detail,
# Schema__EC2__Pricing. Verifies default values and field types.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag                import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Block_Device__Mapping import List__Schema__EC2__Block_Device__Mapping
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Security_Group__Ref   import List__Schema__EC2__Security_Group__Ref
from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State          import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id          import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id     import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type  import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance             import Schema__EC2__Instance
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Instance__Detail     import Schema__EC2__Instance__Detail
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Pricing              import Schema__EC2__Pricing


class Test__Schema__EC2__Instance:

    def test_1__default_state_is_unknown(self):
        inst = Schema__EC2__Instance()
        assert inst.state == Enum__EC2__Instance__State.UNKNOWN

    def test_2__fields_accept_primitives(self):
        inst = Schema__EC2__Instance(
            instance_id   = Safe_Str__EC2__Instance_Id('i-12345678'),
            instance_type = Safe_Str__EC2__Instance__Type('t3.micro'),
            ami_id        = Safe_Str__EC2__AMI_Id('ami-12345678'),
            state         = Enum__EC2__Instance__State.RUNNING,
            name          = 'my-server',
            public_ip     = '1.2.3.4',
        )
        assert str(inst.instance_id)   == 'i-12345678'
        assert str(inst.instance_type) == 't3.micro'
        assert str(inst.ami_id)        == 'ami-12345678'
        assert inst.state              == Enum__EC2__Instance__State.RUNNING
        assert str(inst.name)          == 'my-server'
        assert str(inst.public_ip)     == '1.2.3.4'

    def test_3__default_strings_are_empty(self):
        inst = Schema__EC2__Instance()
        assert str(inst.name)        == ''
        assert str(inst.public_ip)   == ''
        assert str(inst.launch_time) == ''
        assert str(inst.key_name)    == ''


class Test__Schema__EC2__Instance__Detail:

    def test_1__has_extended_fields(self):
        detail = Schema__EC2__Instance__Detail()
        assert hasattr(detail, 'vpc_id')
        assert hasattr(detail, 'subnet_id')
        assert hasattr(detail, 'architecture')
        assert hasattr(detail, 'tags')
        assert hasattr(detail, 'security_groups')
        assert hasattr(detail, 'block_devices')

    def test_2__defaults(self):
        detail = Schema__EC2__Instance__Detail()
        assert detail.state          == Enum__EC2__Instance__State.UNKNOWN
        assert str(detail.vpc_id)    == ''
        assert isinstance(detail.tags,            Dict__EC2__Tag)
        assert isinstance(detail.security_groups, List__Schema__EC2__Security_Group__Ref)
        assert isinstance(detail.block_devices,   List__Schema__EC2__Block_Device__Mapping)
        assert len(detail.tags)            == 0
        assert len(detail.security_groups) == 0
        assert len(detail.block_devices)   == 0


class Test__Schema__EC2__Pricing:

    def test_1__defaults(self):
        pricing = Schema__EC2__Pricing()
        assert str(pricing.currency)         == ''
        assert str(pricing.os)               == ''
        assert str(pricing.price_per_hour)   == ''
        assert str(pricing.price_per_second) == ''

    def test_2__with_values(self):
        pricing = Schema__EC2__Pricing(
            instance_type    = Safe_Str__EC2__Instance__Type('t3.micro'),
            region           = 'us-east-1',
            price_per_hour   = '0.0104',
            price_per_second = '0.000002888',
        )
        assert str(pricing.instance_type)  == 't3.micro'
        assert str(pricing.price_per_hour) == '0.0104'
        assert str(pricing.region)         == 'us-east-1'
