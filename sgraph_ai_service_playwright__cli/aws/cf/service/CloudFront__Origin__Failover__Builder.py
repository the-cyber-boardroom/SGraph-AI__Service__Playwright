# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudFront__Origin__Failover__Builder
# Builds the OriginGroups section of a DistributionConfig dict for a primary +
# fallback origin arrangement (e.g. EC2 → Waker Lambda on 5xx).
# Pure config builder — no boto3, no side effects.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

_DEFAULT_STATUS_CODES = [500, 502, 503, 504]


class CloudFront__Origin__Failover__Builder(Type_Safe):
    group_id           : str  = 'failover-group'                                      # Logical ID for the origin group
    primary_origin_id  : str  = ''                                                    # Must match an existing origin's Id
    fallback_origin_id : str  = ''                                                    # Must match an existing origin's Id

    def build(self, status_codes=None) -> dict:                                       # status_codes: list[int] — HTTP codes that trigger failover
        codes = list(status_codes) if status_codes is not None else _DEFAULT_STATUS_CODES
        return {
            'Quantity': 1,
            'Items'   : [
                {
                    'Id'                        : self.group_id,
                    'FailoverCriteria'          : {
                        'StatusCodes': {
                            'Quantity': len(codes),
                            'Items'   : codes,
                        }
                    },
                    'Members': {
                        'Quantity': 2,
                        'Items'   : [
                            {'OriginId': self.primary_origin_id},
                            {'OriginId': self.fallback_origin_id},
                        ],
                    },
                }
            ],
        }
