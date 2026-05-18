# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — List__Schema__AWS__Tag
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Tag import Schema__AWS__Tag


class List__Schema__AWS__Tag(Type_Safe):
    items : List[Schema__AWS__Tag]
