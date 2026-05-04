# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Delete__Response
# Response for DELETE /v1/ec2/instances/{target}. Returns the ids that were
# sent to AWS for termination. EC2 termination is asynchronous — the resource
# stays visible in SHUTTING_DOWN state for ~1 min before AWS reaps it.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Deploy_Name         import Safe_Str__Deploy_Name
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id


class Schema__Ec2__Delete__Response(Type_Safe):
    target               : Safe_Str__Instance__Id                                   # Echo of the resolved instance id (empty on not-found)
    deploy_name          : Safe_Str__Deploy_Name                                    # Resolved deploy name if known
    terminated_instance_ids : List__Instance__Id                                    # Ids AWS accepted for termination
