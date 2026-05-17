# ═══════════════════════════════════════════════════════════════════════════════
# Tests — IAM__Trust_Policy__Builder
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service  import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Trust_Policy__Builder import IAM__Trust_Policy__Builder


class Test__IAM__Trust_Policy__Builder:

    def _build(self, svc: Enum__IAM__Trust__Service) -> dict:
        return json.loads(IAM__Trust_Policy__Builder().build(svc))

    def test_1__lambda_trust_policy(self):
        doc = self._build(Enum__IAM__Trust__Service.LAMBDA)
        stmt = doc['Statement'][0]
        assert stmt['Principal']['Service'] == 'lambda.amazonaws.com'
        assert stmt['Action']              == 'sts:AssumeRole'

    def test_2__ec2_trust_policy(self):
        doc = self._build(Enum__IAM__Trust__Service.EC2)
        assert doc['Statement'][0]['Principal']['Service'] == 'ec2.amazonaws.com'

    def test_3__ecs_tasks_trust_policy(self):
        doc = self._build(Enum__IAM__Trust__Service.ECS_TASKS)
        assert doc['Statement'][0]['Principal']['Service'] == 'ecs-tasks.amazonaws.com'

    def test_4__api_gateway_trust_policy(self):
        doc = self._build(Enum__IAM__Trust__Service.API_GATEWAY)
        assert doc['Statement'][0]['Principal']['Service'] == 'apigateway.amazonaws.com'
