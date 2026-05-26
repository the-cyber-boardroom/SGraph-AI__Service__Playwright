# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Enum__Assertion__Type (the journey assertion vocabulary)
#
# Discriminator for Schema__Journey__Assertion__* subclasses. Reads-from source
# per type: URL_* read the terminal get_url result; STATUS_CODE/HTTP_HEADER read
# the per-run mitmproxy network log; SELECTOR_* read synthetic wait_for/get_content
# step results (correlation wired in the worker slice).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Assertion__Type(str, Enum):                                             # The journey assertion vocabulary
    URL_CONTAINS          = "url_contains"                                          # terminal URL contains substring
    URL_EQUALS            = "url_equals"                                            # terminal URL equals value
    SELECTOR_VISIBLE      = "selector_visible"                                      # selector appeared (synthetic wait_for)
    SELECTOR_TEXT_EQUALS  = "selector_text_equals"                                  # selector text equals (synthetic get_content)
    SELECTOR_TEXT_CONTAINS= "selector_text_contains"                                # selector text contains (synthetic get_content)
    STATUS_CODE_EQUALS    = "status_code_equals"                                    # a captured flow's status equals value
    HTTP_HEADER_PRESENT   = "http_header_present"                                   # a captured flow carries a header

    def __str__(self): return self.value
