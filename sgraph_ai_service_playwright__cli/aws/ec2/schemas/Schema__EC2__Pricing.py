# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Pricing
# On-demand pricing for an EC2 instance type in a given region.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type   import Safe_Str__EC2__Instance__Type


class Schema__EC2__Pricing(Type_Safe):
    instance_type   : Safe_Str__EC2__Instance__Type
    region          : str                           = ''
    price_per_hour  : str                           = ''    # USD string, e.g. '0.0094'
    price_per_second: str                           = ''    # USD string, e.g. '0.000002611'
    currency        : str                           = 'USD'
    os              : str                           = 'Linux'
