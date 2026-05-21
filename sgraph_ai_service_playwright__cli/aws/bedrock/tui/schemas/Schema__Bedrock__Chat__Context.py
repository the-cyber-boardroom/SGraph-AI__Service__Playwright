# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Context
# The "talk to the data" seam. A labelled block of text seeded into a session as a
# system block — e.g. an sg edge snapshot rendered to markdown, a reality-doc page.
# Pure data — no methods. Labelled in the UI so it is never ambiguous what the model
# was told.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


class Schema__Bedrock__Chat__Context(Type_Safe):
    label : str                                                                   # short UI label, e.g. "edge snapshot @ 10:30"
    body  : str                                                                   # the context text given to the model
