# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__Distribution__Builder
# Pure config builder — produces the DistributionConfig dict required by the
# CloudFront create_distribution / update_distribution API calls.
# No boto3. No side effects. Type_Safe inputs only.
#
# CachingDisabled managed policy: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias               import List__CF__Alias
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Origin__Protocol         import Enum__CF__Origin__Protocol
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class              import Enum__CF__Price__Class

CACHE_POLICY_CACHING_DISABLED = '4135ea2d-6df8-44a3-9df3-4b5a84be39ad'              # AWS-managed CachingDisabled policy
ORIGIN_REQUEST_POLICY_ALL     = 'b689b0a8-53d0-40ab-baf2-68738e2966ac'              # AllViewerExceptHostHeader — forwards query strings + headers


class CloudFront__Distribution__Builder(Type_Safe):
    origin_domain   : str                        = ''                                 # Lambda Function URL hostname (no scheme)
    cert_arn        : str                        = ''                                 # ACM cert ARN in us-east-1
    aliases         : List__CF__Alias                                                 # CNAME aliases e.g. ['*.aws.sg-labs.app']
    comment         : str                        = ''
    price_class     : Enum__CF__Price__Class     = Enum__CF__Price__Class.PriceClass_All
    protocol        : Enum__CF__Origin__Protocol = Enum__CF__Origin__Protocol.HTTPS_ONLY
    enabled         : bool                       = True
    origin_id       : str                        = 'primary'                          # Logical origin ID within this distribution

    def build(self) -> dict:
        config = {
            'CallerReference'   : f'sg-compute-cf-{int(time.time())}',
            'Comment'           : self.comment,
            'DefaultRootObject' : '',
            'Origins'           : {
                'Quantity': 1,
                'Items'   : [self._origin_item()],
            },
            'DefaultCacheBehavior' : self._default_cache_behavior(),
            'Enabled'           : self.enabled,
            'HttpVersion'       : 'http2and3',
            'PriceClass'        : str(self.price_class),
        }
        alias_list = list(self.aliases)
        if alias_list:
            config['Aliases'] = {'Quantity': len(alias_list), 'Items': alias_list}
        else:
            config['Aliases'] = {'Quantity': 0, 'Items': []}
        if self.cert_arn:
            config['ViewerCertificate'] = {
                'ACMCertificateArn'      : self.cert_arn,
                'SSLSupportMethod'       : 'sni-only',
                'MinimumProtocolVersion' : 'TLSv1.2_2021',
            }
        else:
            config['ViewerCertificate'] = {
                'CloudFrontDefaultCertificate': True,
                'MinimumProtocolVersion'      : 'TLSv1.2_2021',
            }
        return config

    def _origin_item(self) -> dict:
        return {
            'Id'                 : self.origin_id,
            'DomainName'         : self.origin_domain,
            'CustomOriginConfig' : {
                'HTTPSPort'             : 443,
                'HTTPPort'              : 80,
                'OriginProtocolPolicy'  : str(self.protocol),
                'OriginSslProtocols'    : {'Quantity': 1, 'Items': ['TLSv1.2']},
            },
        }

    def _default_cache_behavior(self) -> dict:
        return {
            'TargetOriginId'        : self.origin_id,
            'ViewerProtocolPolicy'  : 'redirect-to-https',
            'CachePolicyId'         : CACHE_POLICY_CACHING_DISABLED,
            'OriginRequestPolicyId' : ORIGIN_REQUEST_POLICY_ALL,
            'AllowedMethods'        : {
                'Quantity'     : 7,
                'Items'        : ['HEAD', 'DELETE', 'POST', 'GET', 'OPTIONS', 'PUT', 'PATCH'],
                'CachedMethods': {'Quantity': 2, 'Items': ['HEAD', 'GET']},
            },
            'Compress' : True,
        }
