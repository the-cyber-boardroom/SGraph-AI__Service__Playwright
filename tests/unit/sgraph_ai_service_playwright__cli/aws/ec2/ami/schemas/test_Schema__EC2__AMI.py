# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__EC2__AMI
# Short round-trip + defaults for the AMI schema.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__AMI_Id      import Safe_Str__EC2__AMI_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance_Id import Safe_Str__EC2__Instance_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Snapshot_Id import Safe_Str__EC2__Snapshot_Id
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__AMI              import Schema__EC2__AMI


class Test__Schema__EC2__AMI:

    def test_1__defaults_are_empty(self):
        ami = Schema__EC2__AMI()
        assert str(ami.ami_id)            == ''
        assert str(ami.name)              == ''
        assert str(ami.description)       == ''
        assert str(ami.owner_id)          == ''
        assert str(ami.created_at)        == ''
        assert ami.public                 is False
        assert str(ami.architecture)      == ''
        assert str(ami.root_device_type)  == ''
        assert list(ami.snapshot_ids)     == []
        assert list(ami.attached_instance_ids) == []

    def test_2__fields_accept_primitives(self):
        ami = Schema__EC2__AMI(
            ami_id           = Safe_Str__EC2__AMI_Id('ami-12345678'),
            name             = 'my-image',
            description      = 'a test image',
            owner_id         = '123456789012',
            created_at       = '2026-04-01T00:00:00.000Z',
            public           = False,
            architecture     = 'x86_64',
            root_device_type = 'ebs',
            snapshot_ids     = [Safe_Str__EC2__Snapshot_Id('snap-12345678')],
        )
        assert str(ami.ami_id)              == 'ami-12345678'
        assert str(ami.name)                == 'my-image'
        assert str(ami.snapshot_ids[0])     == 'snap-12345678'
        assert list(ami.attached_instance_ids) == []

    def test_3__attached_instance_ids_appendable(self):
        ami = Schema__EC2__AMI(ami_id=Safe_Str__EC2__AMI_Id('ami-12345678'))
        ami.attached_instance_ids.append(Safe_Str__EC2__Instance_Id('i-12345678'))
        assert str(ami.attached_instance_ids[0]) == 'i-12345678'
