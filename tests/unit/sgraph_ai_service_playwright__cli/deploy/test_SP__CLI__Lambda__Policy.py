# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for SP__CLI__Lambda__Policy
# Asserts the four policy documents are well-formed and tightly scoped. No AWS
# — these are pure Python dicts describing what will be attached when
# SP__CLI__Lambda__Role.ensure() runs.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Policy                                                      import (SP__CLI__Lambda__Policy    ,
                                                                                                                                EC2_ROLE_NAME              ,
                                                                                                                                EC2_SERVICE_PRINCIPAL      ,
                                                                                                                                AGENTIC_CODE_BUCKET_PREFIX ,
                                                                                                                                AGENTIC_CODE_APP_NAME      )


TEST_ACCOUNT = '745506449035'


class test_SP__CLI__Lambda__Policy(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.policy = SP__CLI__Lambda__Policy(aws_account=TEST_ACCOUNT)

    def test__init__(self):
        assert str(self.policy.aws_account) == TEST_ACCOUNT                         # Account id is required — PassRole must be ARN-scoped

    def test_document_ec2_management__shape(self):
        doc = self.policy.document_ec2_management()

        assert doc['Version'] == '2012-10-17'
        sids = {s['Sid'] for s in doc['Statement']}
        assert sids == {'Ec2Describe', 'Ec2RunAndTerminate', 'Ec2SecurityGroupManagement'}

        run = next(s for s in doc['Statement'] if s['Sid'] == 'Ec2RunAndTerminate')
        assert 'ec2:RunInstances'       in run['Action']
        assert 'ec2:TerminateInstances' in run['Action']
        assert 'ec2:CreateTags'         in run['Action']
        assert run['Effect']            == 'Allow'

    def test_document_iam_passrole__scoped_to_ec2_role(self):                       # The key security property — PassRole is NOT '*'
        doc          = self.policy.document_iam_passrole()
        passrole     = next(s for s in doc['Statement'] if s['Sid'] == 'PassPlaywrightEc2Role')
        expected_arn = f'arn:aws:iam::{TEST_ACCOUNT}:role/{EC2_ROLE_NAME}'

        assert passrole['Action']    == 'iam:PassRole'
        assert passrole['Resource']  == expected_arn                                # ARN is bound to the playwright-ec2 role only
        assert passrole['Resource']  != '*'                                         # Explicitly not wildcard
        assert passrole['Condition'] == {'StringEquals': {'iam:PassedToService': EC2_SERVICE_PRINCIPAL}}

    def test_document_iam_passrole__instance_profile_scope(self):
        doc          = self.policy.document_iam_passrole()
        profile      = next(s for s in doc['Statement'] if s['Sid'] == 'InstanceProfileManagement')
        expected_arns = [f'arn:aws:iam::{TEST_ACCOUNT}:role/{EC2_ROLE_NAME}'              ,
                         f'arn:aws:iam::{TEST_ACCOUNT}:instance-profile/{EC2_ROLE_NAME}'  ]

        assert set(profile['Resource']) == set(expected_arns)                       # Both scoped to playwright-ec2 — no blanket access
        assert 'iam:CreateInstanceProfile' in profile['Action']
        assert 'iam:AddRoleToInstanceProfile' in profile['Action']

    def test_document_ecr_read__read_only(self):
        doc   = self.policy.document_ecr_read()
        ecr   = doc['Statement'][0]
        write = [a for a in ecr['Action'] if a.startswith(('ecr:Put', 'ecr:InitiateLayer', 'ecr:Complete', 'ecr:UploadLayer'))]

        assert 'ecr:GetAuthorizationToken' in ecr['Action']
        assert 'ecr:BatchGetImage'         in ecr['Action']
        assert write                        == []                                   # No write actions — pull-only

    def test_document_sts_helpers(self):
        doc = self.policy.document_sts_helpers()
        sts = doc['Statement'][0]
        assert 'sts:GetCallerIdentity'          in sts['Action']
        assert 'sts:DecodeAuthorizationMessage' in sts['Action']

    def test_assume_role_document__lambda_only(self):                               # Trust policy — only the Lambda service can assume the role
        doc       = self.policy.assume_role_document()
        principal = doc['Statement'][0]['Principal']
        assert principal == {'Service': 'lambda.amazonaws.com'}
        assert doc['Statement'][0]['Action'] == 'sts:AssumeRole'

    def test_document_observability__covers_three_services(self):                  # One consolidated policy for AMP + OpenSearch + AMG; read + delete only
        doc  = self.policy.document_observability()
        sids = {s['Sid'] for s in doc['Statement']}
        assert sids == {'AmpReadDelete', 'OpenSearchDescribe', 'OpenSearchHttpRead', 'GrafanaReadDelete'}

        amp      = next(s for s in doc['Statement'] if s['Sid'] == 'AmpReadDelete'     )
        opensrch = next(s for s in doc['Statement'] if s['Sid'] == 'OpenSearchDescribe')
        grafana  = next(s for s in doc['Statement'] if s['Sid'] == 'GrafanaReadDelete' )
        os_http  = next(s for s in doc['Statement'] if s['Sid'] == 'OpenSearchHttpRead')

        assert 'aps:ListWorkspaces'     in amp     ['Action']                       # AMP uses aps: prefix (not amp:)
        assert 'aps:DeleteWorkspace'    in amp     ['Action']
        assert 'es:ListDomainNames'     in opensrch['Action']
        assert 'es:DeleteDomain'        in opensrch['Action']
        assert 'grafana:ListWorkspaces' in grafana ['Action']
        assert 'grafana:DeleteWorkspace'in grafana ['Action']
        assert 'es:ESHttpGet'           in os_http ['Action']                       # SigV4 doc-count call

    def test_document_observability__no_create_or_write_actions(self):              # Read + delete surface only — no create/update paths yet
        doc = self.policy.document_observability()
        for statement in doc['Statement']:
            for action in statement['Action']:
                assert 'Create'  not in action, f'unexpected create action: {action}'
                assert 'Update'  not in action, f'unexpected update action: {action}'
                assert 'Put'     not in action, f'unexpected put action: {action}'
                assert 'Post'    not in action, f'unexpected post action: {action}'

    def test_document_agentic_code_read__scoped_to_app_prefix(self):                # The Lambda only ever reads its own code zip — bucket region wildcarded, key prefix locked to apps/sp-playwright-cli/*
        doc      = self.policy.document_agentic_code_read()
        s3_stmt  = next(s for s in doc['Statement'] if s['Sid'] == 'AgenticCodeRead')
        expected = (f'arn:aws:s3:::{TEST_ACCOUNT}--{AGENTIC_CODE_BUCKET_PREFIX}--*'
                    f'/apps/{AGENTIC_CODE_APP_NAME}/*')

        assert s3_stmt['Effect']   == 'Allow'
        assert s3_stmt['Action']   == ['s3:GetObject']
        assert s3_stmt['Resource'] == expected
        assert s3_stmt['Resource'] != '*'                                            # Never blanket access

    def test_document_agentic_code_read__no_write_actions(self):                    # Read-only - the CI user holds the upload credential, never the Lambda
        doc = self.policy.document_agentic_code_read()
        for statement in doc['Statement']:
            for action in statement['Action']:
                assert action.startswith('s3:Get'), f'unexpected action: {action}'  # GetObject only; HeadObject is implied

    def test_all_documents_are_json_serialisable(self):                             # IAM rejects non-JSON; serialise every doc as a smoke test
        for name in ('document_ec2_management'  , 'document_iam_passrole'    ,
                     'document_ecr_read'        , 'document_sts_helpers'     ,
                     'document_observability'   , 'document_agentic_code_read',
                     'assume_role_document'     ):
            method    = getattr(self.policy, name)
            json_text = json.dumps(method())
            assert isinstance(json_text, str)
            assert len(json_text) > 0
