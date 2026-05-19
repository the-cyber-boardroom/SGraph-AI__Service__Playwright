# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Route_Table_Association
# Association between a Route Table and a Subnet (or the main-table marker).
# `subnet_id` is '' for the implicit "main" association.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Route_Table_Id import Safe_Str__EC2__Route_Table_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Subnet_Id      import Safe_Str__EC2__Subnet_Id


class Schema__EC2__Route_Table_Association(Type_Safe):
    association_id : str = ''                                                   # rtbassoc-… — kept as plain str (no dedicated primitive yet)
    route_table_id : Safe_Str__EC2__Route_Table_Id
    subnet_id      : Safe_Str__EC2__Subnet_Id
    main           : bool = False
