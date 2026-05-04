# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__Stack__Mapper
# Pure mapper — zero AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State      import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client           import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY
from sgraph_ai_service_playwright__cli.docker.service.Docker__Stack__Mapper         import Docker__Stack__Mapper


def _details(stack_name='fast-fermi', allowed_ip='1.2.3.4', state='running', public_ip='5.6.7.8',
             instance_id='i-0123456789abcdef0', sg_id='sg-1234567890abcdef0', name_tag='docker-fast-fermi'):
    return {
        'InstanceId'     : instance_id                                              ,
        'ImageId'        : 'ami-0685f8dd865c8e389'                                  ,
        'InstanceType'   : 't3.medium'                                              ,
        'PublicIpAddress': public_ip                                                 ,
        'State'          : {'Name': state}                                           ,
        'SecurityGroups' : [{'GroupId': sg_id}]                                      ,
        'LaunchTime'     : '2026-04-26T10:00:00+00:00'                               ,
        'Tags'           : [{'Key': 'Name'            , 'Value': name_tag         },
                            {'Key': TAG_STACK_NAME_KEY, 'Value': stack_name        },
                            {'Key': TAG_ALLOWED_IP_KEY, 'Value': allowed_ip        }],
    }


class test_Docker__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = Docker__Stack__Mapper()

    def test_to_info__happy_path(self):
        info = self.mapper.to_info(_details(), 'eu-west-2')
        assert str(info.stack_name)    == 'fast-fermi'
        assert str(info.aws_name_tag)  == 'docker-fast-fermi'
        assert str(info.instance_id)   == 'i-0123456789abcdef0'
        assert str(info.region)        == 'eu-west-2'
        assert str(info.instance_type) == 't3.medium'
        assert str(info.allowed_ip)    == '1.2.3.4'
        assert str(info.public_ip)     == '5.6.7.8'
        assert info.state              == Enum__Docker__Stack__State.RUNNING

    def test_to_info__state_mapping(self):
        for raw, expected in (('pending'      , Enum__Docker__Stack__State.PENDING    ),
                              ('running'      , Enum__Docker__Stack__State.RUNNING    ),
                              ('shutting-down', Enum__Docker__Stack__State.TERMINATING),
                              ('stopping'     , Enum__Docker__Stack__State.STOPPING   ),
                              ('stopped'      , Enum__Docker__Stack__State.STOPPED    ),
                              ('terminated'   , Enum__Docker__Stack__State.TERMINATED )):
            info = self.mapper.to_info(_details(state=raw), 'eu-west-2')
            assert info.state == expected, f'{raw!r} → {expected}'

    def test_to_info__docker_version_empty_on_creation(self):                       # docker_version is populated by health check, not mapper
        info = self.mapper.to_info(_details(), 'eu-west-2')
        assert str(info.docker_version) == ''
