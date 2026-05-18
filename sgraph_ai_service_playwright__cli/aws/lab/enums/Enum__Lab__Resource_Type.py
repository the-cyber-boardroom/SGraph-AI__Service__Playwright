# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Enum__Lab__Resource_Type
# Resource types the lab can create. Teardown order: lower = deleted first.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lab__Resource_Type(str, Enum):
    R53_RECORD       = 'r53-record'        # teardown_order 10
    CF_DISTRIBUTION  = 'cf-distribution'   # teardown_order 30
    LAMBDA           = 'lambda'            # teardown_order 20
    LAMBDA_URL       = 'lambda-url'        # teardown_order 15
    ACM_CERT         = 'acm-cert'          # teardown_order 40
    EC2_INSTANCE     = 'ec2-instance'      # teardown_order 25
    SG               = 'sg'               # teardown_order 50
    IAM_ROLE         = 'iam-role'          # teardown_order 60
    SSM_PARAM        = 'ssm-param'         # teardown_order 5
    S3_BUCKET        = 's3-bucket'         # teardown_order 70

    @property
    def teardown_order(self) -> int:
        _order = {
            'ssm-param'      : 5,
            'r53-record'     : 10,
            'lambda-url'     : 15,
            'lambda'         : 20,
            'ec2-instance'   : 25,
            'cf-distribution': 30,
            'acm-cert'       : 40,
            'sg'             : 50,
            'iam-role'       : 60,
            's3-bucket'      : 70,
        }
        return _order.get(self.value, 99)
