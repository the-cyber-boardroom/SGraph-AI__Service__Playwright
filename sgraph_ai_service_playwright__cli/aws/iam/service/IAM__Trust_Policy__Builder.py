# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — IAM__Trust_Policy__Builder
# Builds IAM trust policy documents (AssumeRolePolicyDocument) for known
# Enum__IAM__Trust__Service values. Returns the JSON string accepted by IAM.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service  import Enum__IAM__Trust__Service


class IAM__Trust_Policy__Builder(Type_Safe):

    def build(self, trust_service: Enum__IAM__Trust__Service) -> str:           # Returns JSON string for AssumeRolePolicyDocument
        doc = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect'   : 'Allow',
                'Principal': {'Service': str(trust_service)},
                'Action'   : 'sts:AssumeRole',
            }]
        }
        return json.dumps(doc)
