# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__Source__Stream__Ref
# Lightweight pointer to a named stream within a source.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Source__Stream__Ref(Type_Safe):
    name        : str = ''
    description : str = ''
    last_event  : str = ''
