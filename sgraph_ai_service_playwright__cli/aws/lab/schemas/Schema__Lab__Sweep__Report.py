# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Sweep__Report
# Summary returned by Lab__Sweeper.sweep() / sg aws lab sweep.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Ledger__Entry import List__Schema__Lab__Ledger__Entry


class Schema__Lab__Sweep__Report(Type_Safe):
    scanned    : int = 0
    leaked     : int = 0
    deleted    : int = 0
    dry_run    : bool = False
    resources  : List__Schema__Lab__Ledger__Entry                                  # resources considered for deletion
