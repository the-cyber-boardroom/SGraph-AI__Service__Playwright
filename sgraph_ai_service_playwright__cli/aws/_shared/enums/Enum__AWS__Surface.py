# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Enum__AWS__Surface
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__AWS__Surface(str, Enum):
    S3          = 's3'
    EC2         = 'ec2'
    FARGATE     = 'fargate'
    BEDROCK     = 'bedrock'
    CLOUDTRAIL  = 'cloudtrail'
    CREDS       = 'creds'
    OBSERVE     = 'observe'
    IAM_GRAPH   = 'iam-graph'
