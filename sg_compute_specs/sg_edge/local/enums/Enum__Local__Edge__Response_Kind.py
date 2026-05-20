# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Enum__Local__Edge__Response_Kind
# The three outcomes the local proxy can return for a request (mirrors the Phase 2
# OpenResty hot-path decision tree: A? TXT? → serve / wake / reject).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Local__Edge__Response_Kind(str, Enum):
    WELCOME        = 'welcome'                                                        # A + TXT present → serve the slug page
    DORMANT        = 'dormant'                                                        # A present, TXT absent → registered but no backend (loading page)
    NOT_RECOGNISED = 'not_recognised'                                                 # A absent → slug not registered (404)

    def __str__(self):
        return self.value
