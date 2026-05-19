# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Schema__EC2__Route_Table
# Schema for an EC2 Route Table, used by the `sg aws ec2 route-table` sub-app.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.collections.Dict__EC2__Tag                                  import Dict__EC2__Tag
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Route                        import List__Schema__EC2__Route
from sgraph_ai_service_playwright__cli.aws.ec2.collections.List__Schema__EC2__Route_Table_Association     import List__Schema__EC2__Route_Table_Association
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Route_Table_Id                    import Safe_Str__EC2__Route_Table_Id
from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__VPC_Id                            import Safe_Str__EC2__VPC_Id


class Schema__EC2__Route_Table(Type_Safe):
    route_table_id : Safe_Str__EC2__Route_Table_Id
    vpc_id         : Safe_Str__EC2__VPC_Id
    routes         : List__Schema__EC2__Route
    associations   : List__Schema__EC2__Route_Table_Association
    tags           : Dict__EC2__Tag
