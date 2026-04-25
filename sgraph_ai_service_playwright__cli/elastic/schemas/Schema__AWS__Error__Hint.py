# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__AWS__Error__Hint
# Pure-data summary of a recognised AWS-side failure, carrying enough text to
# render a friendly CLI message without leaking stack traces. `recognised` is
# False for any exception we don't classify — the CLI re-raises those rather
# than swallowing surprise errors.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List as _List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__AWS__Error__Hint(Type_Safe):
    recognised : bool                  = False
    category   : Safe_Str__Text                                                     # Short tag — single word, no punctuation: 'no-credentials' / 'denied' / 'expired' / 'network' / 'region' / 'clock' / 'unknown'
    headline   : Safe_Str__Diagnostic                                               # One-line summary; preserves slashes, colons, ARNs, em-dash-free punctuation
    body       : Safe_Str__Diagnostic                                               # Sentence; same preservation needs as headline (e.g. an ARN often lands here)
    hints      : _List[str]            = None                                       # Action items, one per line; defaulted to [] in __init__
    exit_code  : int                   = 2                                          # Non-zero, !=1 to distinguish from generic errors
