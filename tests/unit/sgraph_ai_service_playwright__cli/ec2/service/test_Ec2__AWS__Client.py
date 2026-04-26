# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Ec2__AWS__Client
# Module-level pure helpers tested directly. The class methods are tested
# against an in-memory EC2 stub (real subclass, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timedelta, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client                  import (Ec2__AWS__Client                            ,
                                                                                              INSTANCE_STATES_LIVE                         ,
                                                                                              PLAYWRIGHT_IMAGE_NAME                        ,
                                                                                              SIDECAR_IMAGE_NAME                           ,
                                                                                              TAG__DEPLOY_NAME_KEY                         ,
                                                                                              TAG__SERVICE_KEY                             ,
                                                                                              TAG__SERVICE_VALUE                           ,
                                                                                              _ADJECTIVES                                  ,
                                                                                              _SCIENTISTS                                  ,
                                                                                              default_playwright_image_uri                 ,
                                                                                              default_sidecar_image_uri                    ,
                                                                                              ecr_registry_host                            ,
                                                                                              get_creator                                  ,
                                                                                              instance_deploy_name                         ,
                                                                                              instance_tag                                 ,
                                                                                              random_deploy_name                           ,
                                                                                              uptime_str                                   )
from sgraph_ai_service_playwright__cli.ec2.service                                   import Ec2__AWS__Client as aws_client_module


class _Fake_EC2:                                                                    # In-memory stand-in — real class, no mocks. Records every call.
    def __init__(self, instances_details_response=None):
        self.calls                      = []
        self.terminated_instance_ids    = []
        self.instances_details_response = instances_details_response or {}
    def instances_details(self, filters=None):
        self.calls.append(('instances_details', {'filters': filters}))
        return self.instances_details_response
    def instance_terminate(self, instance_id):
        self.calls.append(('instance_terminate', {'instance_id': instance_id}))
        self.terminated_instance_ids.append(instance_id)


def _details(deploy_name='', service_value=TAG__SERVICE_VALUE):                     # Helper to build an osbot-aws instances_details() entry
    tags = []
    if service_value:
        tags.append({'Key': TAG__SERVICE_KEY    , 'Value': service_value})
    if deploy_name:
        tags.append({'Key': TAG__DEPLOY_NAME_KEY, 'Value': deploy_name  })
    return {'tags': tags}


# ──────────────────────────────── module-level helpers ─────────────────────────

class test_random_deploy_name(TestCase):

    def test__shape_is_adjective_dash_scientist(self):
        for _ in range(20):                                                         # secrets.choice — sample to make sure both halves come from the right pool
            name = random_deploy_name()
            adjective, scientist = name.split('-')
            assert adjective in _ADJECTIVES
            assert scientist in _SCIENTISTS

    def test__no_uppercase_or_whitespace(self):
        for _ in range(10):
            name = random_deploy_name()
            assert name == name.lower()
            assert ' ' not in name


class test_get_creator(TestCase):

    def test__returns_a_string(self):                                               # Either git config user.email or $USER fallback or 'unknown'
        result = get_creator()
        assert isinstance(result, str)
        assert result                                                               # Non-empty


class test_uptime_str(TestCase):

    def test__none_returns_question_mark(self):
        assert uptime_str(None) == '?'

    def test__empty_string_returns_question_mark(self):
        assert uptime_str('')   == '?'

    def test__non_datetime_returns_question_mark(self):                             # Defensive: AWS sometimes hands back a string we don't expect
        assert uptime_str('2026-04-26T10:00:00Z') == '?'

    def test__future_launch_time_returns_question_mark(self):                       # Negative seconds: clock skew or test fixture mistake
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        assert uptime_str(future) == '?'

    def test__minutes_format(self):
        recent = datetime.now(timezone.utc) - timedelta(minutes=37)
        assert uptime_str(recent) == '37m'

    def test__hours_format(self):
        a_few_hours = datetime.now(timezone.utc) - timedelta(hours=3, minutes=17)
        assert uptime_str(a_few_hours) == '3h 17m'

    def test__days_format(self):
        days_old = datetime.now(timezone.utc) - timedelta(days=2, hours=5)
        assert uptime_str(days_old) == '2d 5h'

    def test__naive_datetime_treated_as_utc(self):                                  # AWS LaunchTime can come back without tzinfo
        naive_recent = datetime.utcnow() - timedelta(minutes=10)
        assert uptime_str(naive_recent) == '10m'


# ──────────────────────────────── AWS context accessors (Phase A step 3b) ─────

class test_aws_context_accessors(TestCase):                                         # AWS_Config provides cached account + region; we patch it via the module-level functions

    def setUp(self):
        self._orig_account = aws_client_module.aws_account_id
        self._orig_region  = aws_client_module.aws_region

    def tearDown(self):
        aws_client_module.aws_account_id = self._orig_account
        aws_client_module.aws_region     = self._orig_region

    def test_ecr_registry_host__assembled_from_account_and_region(self):
        aws_client_module.aws_account_id = lambda: '123456789012'
        aws_client_module.aws_region     = lambda: 'eu-west-2'
        assert aws_client_module.ecr_registry_host() == '123456789012.dkr.ecr.eu-west-2.amazonaws.com'

    def test_default_playwright_image_uri__uses_playwright_image_name(self):
        aws_client_module.aws_account_id = lambda: '111122223333'
        aws_client_module.aws_region     = lambda: 'us-east-1'
        expected = f'111122223333.dkr.ecr.us-east-1.amazonaws.com/{PLAYWRIGHT_IMAGE_NAME}:latest'
        assert aws_client_module.default_playwright_image_uri() == expected

    def test_default_sidecar_image_uri__uses_sidecar_image_name(self):
        aws_client_module.aws_account_id = lambda: '111122223333'
        aws_client_module.aws_region     = lambda: 'us-east-1'
        expected = f'111122223333.dkr.ecr.us-east-1.amazonaws.com/{SIDECAR_IMAGE_NAME}:latest'
        assert aws_client_module.default_sidecar_image_uri() == expected

    def test_image_name_constants_are_distinct(self):                               # Defensive: catches future copy-paste bugs in the import block
        assert PLAYWRIGHT_IMAGE_NAME != SIDECAR_IMAGE_NAME
        assert PLAYWRIGHT_IMAGE_NAME                                                # Non-empty
        assert SIDECAR_IMAGE_NAME


class test_instance_tag(TestCase):

    def test__returns_value_when_key_present(self):
        details = {'tags': [{'Key': 'sg:deploy-name', 'Value': 'happy-turing'}]}
        assert instance_tag(details, 'sg:deploy-name') == 'happy-turing'

    def test__returns_empty_string_when_key_missing(self):
        details = {'tags': [{'Key': 'other-key', 'Value': 'v'}]}
        assert instance_tag(details, 'sg:deploy-name') == ''

    def test__returns_empty_string_when_no_tags_key(self):                          # osbot-aws uses lowercase 'tags' (not boto3's 'Tags')
        assert instance_tag({}, 'sg:deploy-name') == ''

    def test__instance_deploy_name_uses_correct_key(self):
        details = _details(deploy_name='quick-fermi')
        assert instance_deploy_name(details) == 'quick-fermi'


# ──────────────────────────────── Ec2__AWS__Client class methods ───────────────

class test_Ec2__AWS__Client(TestCase):

    def setUp(self):
        self.fake_ec2     = _Fake_EC2()
        self.aws          = Ec2__AWS__Client()
        self.aws.ec2      = lambda: self.fake_ec2                                   # In-memory composition seam (Type_Safe allows attribute override at instance level)

    def test_find_instances__filters_by_service_tag_and_live_states(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='happy-turing')}
        result = self.aws.find_instances()

        assert result == {'i-aaa': _details(deploy_name='happy-turing')}
        assert len(self.fake_ec2.calls) == 1
        op, kwargs = self.fake_ec2.calls[0]
        assert op == 'instances_details'
        filters = {f['Name']: f['Values'] for f in kwargs['filters']}
        assert filters[f'tag:{TAG__SERVICE_KEY}'] == [TAG__SERVICE_VALUE]
        assert filters['instance-state-name']    == INSTANCE_STATES_LIVE

    def test_find_instances__none_response_normalised_to_empty_dict(self):
        self.fake_ec2.instances_details_response = None
        assert self.aws.find_instances() == {}

    def test_find_instance_ids(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='a'),
                                                    'i-bbb': _details(deploy_name='b')}
        ids = self.aws.find_instance_ids()
        assert sorted(ids) == ['i-aaa', 'i-bbb']

    def test_resolve_instance_id__instance_id_passes_through(self):                 # Even without an AWS call
        assert self.aws.resolve_instance_id('i-1234567890abcdef0') == 'i-1234567890abcdef0'
        assert self.fake_ec2.calls == []                                            # No AWS lookup needed

    def test_resolve_instance_id__deploy_name_resolves(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='happy-turing'),
                                                    'i-bbb': _details(deploy_name='quick-fermi'  )}
        assert self.aws.resolve_instance_id('quick-fermi') == 'i-bbb'

    def test_resolve_instance_id__missing_deploy_name_raises(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='happy-turing')}
        with self.assertRaises(ValueError) as ctx:
            self.aws.resolve_instance_id('not-a-real-name')
        assert "'not-a-real-name'" in str(ctx.exception)

    def test_terminate_instances__no_nickname_kills_all(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='a'),
                                                    'i-bbb': _details(deploy_name='b')}
        result = self.aws.terminate_instances()
        assert sorted(result)                            == ['i-aaa', 'i-bbb']
        assert sorted(self.fake_ec2.terminated_instance_ids) == ['i-aaa', 'i-bbb']

    def test_terminate_instances__nickname_kills_only_match(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='a'),
                                                    'i-bbb': _details(deploy_name='b')}
        result = self.aws.terminate_instances(nickname='b')
        assert result == ['i-bbb']
        assert self.fake_ec2.terminated_instance_ids == ['i-bbb']

    def test_terminate_instances__nickname_no_match_kills_nothing(self):
        self.fake_ec2.instances_details_response = {'i-aaa': _details(deploy_name='a')}
        result = self.aws.terminate_instances(nickname='not-here')
        assert result == []
        assert self.fake_ec2.terminated_instance_ids == []
