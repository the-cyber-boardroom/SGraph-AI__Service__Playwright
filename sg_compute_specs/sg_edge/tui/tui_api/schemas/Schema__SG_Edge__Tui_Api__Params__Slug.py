# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui/tui_api: Schema__SG_Edge__Tui_Api__Params__Slug
# Params for the slug-targeting actions (request / register / unregister). Type_Safe
# validates on construction; Tui_Api__Schema__Builder emits its JSON Schema for the
# model. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__SG_Edge__Tui_Api__Params__Slug(Type_Safe):
    slug : str                                                                       # the slug to act on (e.g. 'alice')
