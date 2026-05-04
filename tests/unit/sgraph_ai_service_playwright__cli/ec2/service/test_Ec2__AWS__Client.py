# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Ec2__AWS__Client
# Module-level pure helpers tested directly. The class methods are tested
# against an in-memory EC2 stub (real subclass, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timedelta, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client                  import (Ec2__AWS__Client                            ,
                                                                                              EC2__AMI_NAME_AL2023                         ,
                                                                                              EC2__AMI_OWNER_AMAZON                        ,
                                                                                              EC2__HOST_CONTROL_PORT                       ,
                                                                                              EC2__PLAYWRIGHT_PORT                         ,
                                                                                              EC2__SIDECAR_ADMIN_PORT                      ,
                                                                                              IAM__ASSUME_ROLE_SERVICE                     ,
                                                                                              IAM__ECR_READONLY_POLICY_ARN                 ,
                                                                                              IAM__OBSERVABILITY_POLICY_ARNS               ,
                                                                                              IAM__PASSROLE_POLICY_NAME                    ,
                                                                                              IAM__POLICY_ARNS                             ,
                                                                                              IAM__PROMETHEUS_RW_POLICY_ARN                ,
                                                                                              IAM__ROLE_NAME                               ,
                                                                                              IAM__SSM_CORE_POLICY_ARN                     ,
                                                                                              INSTANCE_STATES_LIVE                         ,
                                                                                              PLAYWRIGHT_IMAGE_NAME                        ,
                                                                                              SG_INGRESS_PORTS                             ,
                                                                                              SG__DESCRIPTION                              ,
                                                                                              SG__NAME                                     ,
                                                                                              SIDECAR_IMAGE_NAME                           ,
                                                                                              TAG__AMI_STATUS_KEY                          ,
                                                                                              TAG__DEPLOY_NAME_KEY                         ,
                                                                                              TAG__SERVICE_KEY                             ,
                                                                                              TAG__SERVICE_VALUE                           ,
                                                                                              _ADJECTIVES                                  ,
                                                                                              _SCIENTISTS                                  ,
                                                                                              decode_aws_auth_error                        ,
                                                                                              default_playwright_image_uri                 ,
                                                                                              default_sidecar_image_uri                    ,
                                                                                              ecr_registry_host                            ,
                                                                                              get_creator                                  ,
                                                                                              instance_deploy_name                         ,
                                                                                              instance_tag                                 ,
                                                                                              random_deploy_name                           ,
                                                                                              uptime_str                                   )
from sgraph_ai_service_playwright__cli.ec2.service                                   import Ec2__AWS__Client as aws_client_module


class _Fake_Boto3_Client:                                                           # In-memory stand-in for ec2.client() — used by AMI lifecycle methods that drop down to raw boto3
    def __init__(self):
        self.calls               = []
        self.create_image_resp   = {'ImageId': 'ami-fake-001'}
        self.describe_images_resp = {'Images': []}
    def create_image(self, **kwargs):
        self.calls.append(('create_image', kwargs))
        return self.create_image_resp
    def describe_images(self, **kwargs):
        self.calls.append(('describe_images', kwargs))
        return self.describe_images_resp
    def create_tags(self, **kwargs):
        self.calls.append(('create_tags', kwargs))


class _Fake_EC2:                                                                    # In-memory stand-in — real class, no mocks. Records every call.
    def __init__(self, instances_details_response=None):
        self.calls                      = []
        self.terminated_instance_ids    = []
        self.instances_details_response = instances_details_response or {}
        self.security_group_response    = None                                      # None ⇒ "create needed"; dict ⇒ "already exists"
        self.security_group_create_resp = {'data': {'security_group_id': 'sg-fake'}}
        self.amis_response              = []
        self.boto3_client               = _Fake_Boto3_Client()
    def instances_details(self, filters=None):
        self.calls.append(('instances_details', {'filters': filters}))
        return self.instances_details_response
    def instance_terminate(self, instance_id):
        self.calls.append(('instance_terminate', {'instance_id': instance_id}))
        self.terminated_instance_ids.append(instance_id)
    def security_group(self, security_group_name):
        self.calls.append(('security_group', {'name': security_group_name}))
        return self.security_group_response
    def security_group_create(self, security_group_name, description):
        self.calls.append(('security_group_create', {'name': security_group_name, 'description': description}))
        return self.security_group_create_resp
    def security_group_authorize_ingress(self, security_group_id, port):
        self.calls.append(('security_group_authorize_ingress', {'sg_id': security_group_id, 'port': port}))
    def amis(self, owner, name, architecture):
        self.calls.append(('amis', {'owner': owner, 'name': name, 'architecture': architecture}))
        return self.amis_response
    def client(self):
        return self.boto3_client


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


# ──────────────────────────────── IAM constants + decoder (Phase A step 3c) ───

class test_iam_constants(TestCase):

    def test__role_name_does_not_start_with_sg_prefix(self):                        # AWS reserves 'sg-*' for SG IDs only — applies to IAM names too via convention
        assert not IAM__ROLE_NAME.startswith('sg-')
        assert IAM__ROLE_NAME == 'playwright-ec2'

    def test__passrole_policy_name_uniquely_namespaced(self):
        assert IAM__PASSROLE_POLICY_NAME == 'sg-playwright-passrole-ec2'             # Underscore-prefixed names get rejected by IAM

    def test__assume_role_service_is_ec2(self):                                     # Trust policy must allow EC2 to assume the role
        assert IAM__ASSUME_ROLE_SERVICE == 'ec2.amazonaws.com'

    def test__policy_arns_tuple_contains_ecr_and_ssm(self):
        assert IAM__ECR_READONLY_POLICY_ARN.endswith('AmazonEC2ContainerRegistryReadOnly')
        assert IAM__SSM_CORE_POLICY_ARN    .endswith('AmazonSSMManagedInstanceCore')
        assert IAM__POLICY_ARNS == (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)

    def test__observability_policy_arns_only_contains_prometheus_rw(self):           # OpenSearch write is domain-specific — added via resource policy, not here
        assert IAM__PROMETHEUS_RW_POLICY_ARN.endswith('AmazonPrometheusRemoteWriteAccess')
        assert IAM__OBSERVABILITY_POLICY_ARNS == (IAM__PROMETHEUS_RW_POLICY_ARN,)


class test_decode_aws_auth_error(TestCase):

    def test__no_encoded_blob_returns_empty_string(self):                           # Generic exceptions don't carry an encoded message — short-circuit
        assert decode_aws_auth_error(RuntimeError('something else'))   == ''
        assert decode_aws_auth_error(ValueError('AccessDenied: nope')) == ''

    def test__sts_call_failure_swallowed_to_empty_string(self):                     # Defensive: don't blow up the caller's error path if the decode itself fails
        exc = RuntimeError('UnauthorizedOperation. Encoded authorization failure message: NOT-A-VALID-BLOB')
        assert decode_aws_auth_error(exc) == ''                                     # boto3 raises in the test env (no creds); function catches and returns ''


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

    # ── Security group (Phase A step 3d) ─────────────────────────────────────

    def test_ensure_security_group__creates_when_missing(self):
        self.fake_ec2.security_group_response = None                                # Triggers create path
        sg_id = self.aws.ensure_security_group()
        assert sg_id == 'sg-fake'
        ops   = [c[0] for c in self.fake_ec2.calls]
        assert ops == ['security_group', 'security_group_create',
                       'security_group_authorize_ingress', 'security_group_authorize_ingress',
                       'security_group_authorize_ingress']                                        # 3 ingress ports: 8000 + 8001 + 9000 (host control plane)
        port_calls = [c[1]['port'] for c in self.fake_ec2.calls if c[0] == 'security_group_authorize_ingress']
        assert port_calls == list(SG_INGRESS_PORTS)                                 # Authorises every ingress port in the canonical order

    def test_ensure_security_group__reuses_existing(self):
        self.fake_ec2.security_group_response = {'GroupId': 'sg-existing'}          # Already-exists path
        sg_id = self.aws.ensure_security_group()
        assert sg_id == 'sg-existing'
        ops   = [c[0] for c in self.fake_ec2.calls]
        assert 'security_group_create' not in ops                                   # Skipped because the SG already exists

    def test_ensure_security_group__ingress_failure_is_swallowed(self):             # 'rule already exists' is the typical case — must not break create
        original_authorize = self.fake_ec2.security_group_authorize_ingress
        def boom(security_group_id, port):
            original_authorize(security_group_id=security_group_id, port=port)
            raise RuntimeError('InvalidPermission.Duplicate')
        self.fake_ec2.security_group_authorize_ingress = boom
        sg_id = self.aws.ensure_security_group()
        assert sg_id == 'sg-fake'                                                   # Returned successfully despite per-port raises

    # ── AMI lifecycle (Phase A step 3d) ───────────────────────────────────────

    def test_latest_al2023_ami_id__returns_most_recent_by_creation_date(self):
        self.fake_ec2.amis_response = [
            {'ImageId': 'ami-old', 'CreationDate': '2024-01-01T00:00:00Z'},
            {'ImageId': 'ami-new', 'CreationDate': '2026-04-01T00:00:00Z'},
            {'ImageId': 'ami-mid', 'CreationDate': '2025-06-01T00:00:00Z'},
        ]
        assert self.aws.latest_al2023_ami_id() == 'ami-new'
        amis_call = next(c for c in self.fake_ec2.calls if c[0] == 'amis')
        assert amis_call[1] == {'owner': EC2__AMI_OWNER_AMAZON, 'name': EC2__AMI_NAME_AL2023, 'architecture': 'x86_64'}

    def test_latest_al2023_ami_id__raises_when_no_ami_found(self):
        self.fake_ec2.amis_response = []
        with self.assertRaises(RuntimeError) as ctx:
            self.aws.latest_al2023_ami_id()
        assert EC2__AMI_NAME_AL2023 in str(ctx.exception)

    def test_create_ami__tags_with_service_and_untested_status(self):
        self.fake_ec2.boto3_client.create_image_resp = {'ImageId': 'ami-baked-1'}
        ami_id = self.aws.create_ami('i-aaa', 'sgpl-baked-2026-04-26')
        assert ami_id == 'ami-baked-1'

        op, kwargs = self.fake_ec2.boto3_client.calls[0]
        assert op == 'create_image'
        assert kwargs['InstanceId'] == 'i-aaa'
        assert kwargs['Name']       == 'sgpl-baked-2026-04-26'
        assert kwargs['NoReboot']   is True
        tags = {t['Key']: t['Value'] for t in kwargs['TagSpecifications'][0]['Tags']}
        assert tags['Name']                  == 'sgpl-baked-2026-04-26'
        assert tags[TAG__SERVICE_KEY]        == TAG__SERVICE_VALUE
        assert tags[TAG__AMI_STATUS_KEY]     == 'untested'

    def test_tag_ami__overwrites_status_tag(self):
        self.aws.tag_ami('ami-x', 'healthy')
        op, kwargs = self.fake_ec2.boto3_client.calls[0]
        assert op == 'create_tags'
        assert kwargs['Resources']  == ['ami-x']
        assert kwargs['Tags']       == [{'Key': TAG__AMI_STATUS_KEY, 'Value': 'healthy'}]

    def test_latest_healthy_ami__returns_most_recent_healthy(self):
        self.fake_ec2.boto3_client.describe_images_resp = {'Images': [
            {'ImageId': 'ami-h-old', 'CreationDate': '2025-01-01T00:00:00Z'},
            {'ImageId': 'ami-h-new', 'CreationDate': '2026-04-01T00:00:00Z'},
        ]}
        result = self.aws.latest_healthy_ami()
        assert result == 'ami-h-new'

        op, kwargs = self.fake_ec2.boto3_client.calls[0]
        assert op == 'describe_images'
        filters = {f['Name']: f['Values'] for f in kwargs['Filters']}
        assert filters[f'tag:{TAG__SERVICE_KEY}']    == [TAG__SERVICE_VALUE]
        assert filters[f'tag:{TAG__AMI_STATUS_KEY}'] == ['healthy']
        assert filters['state']                     == ['available']
        assert kwargs['Owners']                     == ['self']

    def test_latest_healthy_ami__returns_none_when_no_match(self):
        self.fake_ec2.boto3_client.describe_images_resp = {'Images': []}
        assert self.aws.latest_healthy_ami() is None


# ──────────────────────────────── SG / AMI constants ──────────────────────────

class test_sg_and_ami_constants(TestCase):

    def test__sg_name_does_not_start_with_reserved_sg_prefix(self):                 # CLAUDE.md AWS Resource Naming rule #14
        assert not SG__NAME.startswith('sg-')
        assert SG__NAME == 'playwright-ec2'

    def test__sg_description_is_ascii_only(self):                                   # AWS rejects non-ASCII GroupDescription (em-dash, etc.)
        try:
            SG__DESCRIPTION.encode('ascii')
        except UnicodeEncodeError as exc:
            self.fail(f'SG__DESCRIPTION must be ASCII (AWS rejects multi-byte): {exc}')

    def test__sg_ingress_ports_are_canonical(self):
        assert SG_INGRESS_PORTS == (EC2__PLAYWRIGHT_PORT, EC2__SIDECAR_ADMIN_PORT, EC2__HOST_CONTROL_PORT)
        assert EC2__PLAYWRIGHT_PORT       == 8000
        assert EC2__SIDECAR_ADMIN_PORT    == 8001

    def test__ami_name_filter_targets_al2023(self):
        assert EC2__AMI_OWNER_AMAZON == 'amazon'
        assert EC2__AMI_NAME_AL2023.startswith('al2023-ami-')

    def test__ami_status_tag_key_is_namespaced(self):
        assert TAG__AMI_STATUS_KEY == 'sg:ami-status'                               # sg: prefix matches the rest of the tag conventions
