# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish schemas: Schema__Vault_Publish__Bootstrap__Request
# Fields: cert_arn (ACM wildcard ARN), zone (DNS apex), role_arn (Lambda exec role).
# No namespace field — flat subdomain scheme only.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

DEFAULT_CERT_ARN = 'arn:aws:acm:us-east-1:745506449035:certificate/99346343-dc1e-4a62-a6d3-0f22ab7bfffa'
DEFAULT_ZONE     = 'aws.sg-labs.app'


class Schema__Vault_Publish__Bootstrap__Request(Type_Safe):
    cert_arn : str = DEFAULT_CERT_ARN
    zone     : str = DEFAULT_ZONE
    role_arn : str = ''
