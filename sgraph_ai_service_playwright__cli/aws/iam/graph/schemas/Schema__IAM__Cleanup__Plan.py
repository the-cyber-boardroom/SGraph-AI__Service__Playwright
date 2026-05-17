# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Cleanup__Plan
# Describes what will be (or was) deleted in a cleanup pass.
# Pure data. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.collections.List__Schema__IAM__Graph__Node import List__Schema__IAM__Graph__Node


class Schema__IAM__Cleanup__Plan(Type_Safe):
    candidates      : List__Schema__IAM__Graph__Node   # roles/entities to delete
    dry_run         : bool = True                      # always True unless --confirm passed
    skipped_service_linked : int = 0                   # count filtered out (cannot delete via API)
    skipped_cascade_risk   : int = 0                   # count filtered out (active resource attachments)
    executed        : bool = False                     # True after real delete completes
    deleted_count   : int  = 0
    error_count     : int  = 0
