# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Schema__Edit__Diff
#
# Container for the list of diff items returned by Edit__Diff.diff().
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Diff__Item               import Schema__Edit__Diff__Item


class Schema__Edit__Diff(Type_Safe):

    items      : List[Schema__Edit__Diff__Item] = None
    has_changes: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.items is None:
            self.items = []
