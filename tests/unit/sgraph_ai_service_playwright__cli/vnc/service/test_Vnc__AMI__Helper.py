# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__AMI__Helper
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AMI__Helper                 import (AL2023_NAME_FILTER ,
                                                                                              AMAZON_OWNER       ,
                                                                                              Vnc__AMI__Helper   )


class _Fake_Boto_EC2:
    def __init__(self):
        self.calls           = []
        self.images_response = {'Images': []}
    def describe_images(self, **kw):
        self.calls.append(('describe_images', kw))
        return self.images_response


class test_Vnc__AMI__Helper(TestCase):

    def setUp(self):
        self.fake = _Fake_Boto_EC2()
        self.ami  = Vnc__AMI__Helper()
        self.ami.ec2_client = lambda region: self.fake

    def test_latest_al2023__returns_most_recent(self):
        self.fake.images_response = {'Images': [
            {'ImageId': 'ami-old', 'CreationDate': '2024-01-01T00:00:00Z'},
            {'ImageId': 'ami-new', 'CreationDate': '2026-04-01T00:00:00Z'},
        ]}
        assert self.ami.latest_al2023_ami_id('eu-west-2') == 'ami-new'

        kw = self.fake.calls[0][1]
        assert kw['Owners'] == [AMAZON_OWNER]
        filters = {f['Name']: f['Values'] for f in kw['Filters']}
        assert filters['name']         == [AL2023_NAME_FILTER]
        assert filters['architecture'] == ['x86_64']

    def test_latest_al2023__raises_when_no_ami(self):
        self.fake.images_response = {'Images': []}
        with self.assertRaises(RuntimeError) as ctx:
            self.ami.latest_al2023_ami_id('eu-west-2')
        assert 'eu-west-2' in str(ctx.exception)

    def test_latest_healthy__filter_shape(self):
        self.fake.images_response = {'Images': [{'ImageId': 'ami-h', 'CreationDate': '2026-04-01T00:00:00Z'}]}
        assert self.ami.latest_healthy_ami_id('eu-west-2') == 'ami-h'
        kw = self.fake.calls[0][1]
        filters = {f['Name']: f['Values'] for f in kw['Filters']}
        assert filters['tag:sg:purpose']    == ['vnc']                              # Filtered to our section
        assert filters['tag:sg:ami-status'] == ['healthy']

    def test_latest_healthy__empty_string_when_none(self):
        self.fake.images_response = {'Images': []}
        assert self.ami.latest_healthy_ami_id('eu-west-2') == ''
