# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for CI__User__Passrole.build_policy_document
# The policy builder is pure Python — no AWS required. The ensure() path
# needs real STS + IAM and is exercised in CI against live AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.deploy.CI__User__Passrole                    import (CI__User__Passrole        ,
                                                                                           CI_PASSROLE_POLICY_NAME    )
from sgraph_ai_service_playwright__cli.deploy.SP__CLI__Lambda__Role                 import ASSUME_ROLE_SERVICE


TEST_ROLE_ARN = 'arn:aws:iam::745506449035:role/sp-playwright-cli-lambda'


class test_CI__User__Passrole(TestCase):

    def setUp(self):
        self.helper = CI__User__Passrole()

    def test__policy_name_is_stable(self):                                          # Name is the identity of the inline policy on the user — must not drift
        assert CI_PASSROLE_POLICY_NAME == 'sg-playwright-cli-passrole'

    def test__build_policy_document__shape(self):
        doc = self.helper.build_policy_document(TEST_ROLE_ARN)

        assert doc['Version']              == '2012-10-17'
        assert len(doc['Statement'])       == 1
        statement = doc['Statement'][0]
        assert statement['Sid']            == 'PassRoleToLambdaOnly'
        assert statement['Effect']         == 'Allow'
        assert statement['Action']         == 'iam:PassRole'
        assert statement['Resource']       == TEST_ROLE_ARN                         # Pinned to the one role — NOT '*'
        assert statement['Resource']       != '*'

    def test__build_policy_document__condition_locks_to_lambda(self):               # Condition is the second half of the narrow-scope guarantee — without it, the user could pass the role to ANY service
        doc       = self.helper.build_policy_document(TEST_ROLE_ARN)
        condition = doc['Statement'][0]['Condition']
        assert condition == {'StringEquals': {'iam:PassedToService': ASSUME_ROLE_SERVICE}}
        assert ASSUME_ROLE_SERVICE == 'lambda.amazonaws.com'
