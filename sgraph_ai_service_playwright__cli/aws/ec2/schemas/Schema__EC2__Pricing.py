# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Pricing
# On-demand pricing for an EC2 instance type in a given region.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                      import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region       import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Currency         import Safe_Str__EC2__Currency
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type   import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__OS               import Safe_Str__EC2__OS
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Price            import Safe_Str__EC2__Price


class Schema__EC2__Pricing(Type_Safe):
    instance_type   : Safe_Str__EC2__Instance__Type
    region          : Safe_Str__AWS__Region
    price_per_hour  : Safe_Str__EC2__Price             # USD string, e.g. '0.0094'
    price_per_second: Safe_Str__EC2__Price             # USD string, e.g. '0.000002611'
    currency        : Safe_Str__EC2__Currency
    os              : Safe_Str__EC2__OS
