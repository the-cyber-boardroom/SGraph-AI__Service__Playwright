# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__Stack__Mapper
# Pure mapper — zero AWS calls. Tests assert dict-shape → schema-shape.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client   import TAG_ALLOWED_IP_KEY, TAG_STACK_NAME_KEY
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Stack__Mapper import OpenSearch__Stack__Mapper


def _details(stack_name='os-quiet-fermi', allowed_ip='1.2.3.4', state='running', public_ip='5.6.7.8',
             instance_id='i-0123456789abcdef0', sg_id='sg-1234567890abcdef0', name_tag='opensearch-quiet-fermi'):
    return {
        'InstanceId'     : instance_id                                                    ,
        'ImageId'        : 'ami-0685f8dd865c8e389'                                        ,
        'InstanceType'   : 'm6i.large'                                                    ,
        'PublicIpAddress': public_ip                                                       ,
        'State'          : {'Name': state}                                                 ,
        'SecurityGroups' : [{'GroupId': sg_id}]                                            ,
        'LaunchTime'     : '2026-04-26 10:00:00+00:00'                                     ,
        'Tags'           : [{'Key': 'Name'              , 'Value': name_tag             },
                            {'Key': TAG_STACK_NAME_KEY  , 'Value': stack_name           },
                            {'Key': TAG_ALLOWED_IP_KEY  , 'Value': allowed_ip           }],
    }


class test_OpenSearch__Stack__Mapper(TestCase):

    def setUp(self):
        self.mapper = OpenSearch__Stack__Mapper()

    def test_to_info__happy_path(self):
        info = self.mapper.to_info(_details(), 'eu-west-2')
        assert str(info.stack_name)        == 'os-quiet-fermi'
        assert str(info.aws_name_tag)      == 'opensearch-quiet-fermi'
        assert str(info.instance_id)       == 'i-0123456789abcdef0'
        assert str(info.region)            == 'eu-west-2'
        assert str(info.instance_type)     == 'm6i.large'
        assert str(info.allowed_ip)        == '1.2.3.4'
        assert str(info.public_ip)         == '5.6.7.8'
        assert str(info.dashboards_url)    == 'https://5.6.7.8/'
        assert str(info.os_endpoint)       == 'https://5.6.7.8:9200/'
        assert info.state                  == Enum__OS__Stack__State.RUNNING

    def test_to_info__no_public_ip_yields_empty_urls(self):
        d = _details(public_ip='')
        info = self.mapper.to_info(d, 'eu-west-2')
        assert str(info.public_ip)      == ''
        assert str(info.dashboards_url) == ''                                       # No URL until AWS assigns the IP
        assert str(info.os_endpoint)    == ''

    def test_to_info__missing_security_groups_yields_empty_sg(self):
        d = _details()
        d['SecurityGroups'] = []
        info = self.mapper.to_info(d, 'eu-west-2')
        assert str(info.security_group_id) == ''

    def test_to_info__state_mapping(self):                                          # Lifecycle vocabulary lock-in
        for raw, expected in (('pending'      , Enum__OS__Stack__State.PENDING    ),
                              ('running'      , Enum__OS__Stack__State.RUNNING    ),
                              ('shutting-down', Enum__OS__Stack__State.TERMINATING),
                              ('stopping'     , Enum__OS__Stack__State.TERMINATING),
                              ('stopped'      , Enum__OS__Stack__State.TERMINATED ),
                              ('terminated'   , Enum__OS__Stack__State.TERMINATED )):
            info = self.mapper.to_info(_details(state=raw), 'eu-west-2')
            assert info.state == expected, f'{raw} did not map to {expected}'

    def test_to_info__unknown_state_falls_through(self):
        info = self.mapper.to_info(_details(state='cosmic-ray'), 'eu-west-2')
        assert info.state == Enum__OS__Stack__State.UNKNOWN
