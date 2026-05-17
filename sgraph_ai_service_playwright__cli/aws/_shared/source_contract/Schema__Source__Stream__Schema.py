# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__Source__Stream__Schema
# Describes the field layout of a named stream.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Source__Field(Type_Safe):
    name     : str = ''
    type_hint: str = ''
    nullable : bool = True


class Schema__Source__Stream__Schema(Type_Safe):
    stream : str = ''
    fields : List[Schema__Source__Field]
