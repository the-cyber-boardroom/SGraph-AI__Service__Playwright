# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: bedrock_chat_tui__config
# Shared constants for the Bedrock chat TUI. Cost is a first-class concern: the
# session budget is visible and ephemeral (discarded on close).
#
# Nova-only for v1 — the model picker and resolver are filtered to PROVIDER. Adding
# other providers later is a one-line change here plus widening the picker.
# ═══════════════════════════════════════════════════════════════════════════════

PROVIDER             = 'nova'                                                     # v1: Nova only
DEFAULT_MODEL_ALIAS  = 'default'                                                  # resolves to amazon.nova-lite-v1:0
DEFAULT_BUDGET_USD   = 0.50                                                       # soft session budget shown on the meter
BUDGET_WARN_FRACTION = 0.70                                                       # amber at 70 %
BUDGET_OVER_FRACTION = 0.90                                                       # red at 90 %
CARD_WIDTH           = 64                                                         # ASCII export card inner width
TITLE                = 'sg aws bedrock chat'
