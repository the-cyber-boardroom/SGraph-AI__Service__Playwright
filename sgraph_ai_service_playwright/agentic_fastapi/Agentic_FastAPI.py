# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_FastAPI — L1 base class (v0.1.29, first-pass agentic refactor)
#
# Generic FastAPI base that every "agentic" app extends. Today it is a thin
# layer over Serverless__Fast_API — no added routes, no added middleware. It
# exists so that:
#
#   1. All agentic apps share a single ancestor, which is where the admin
#      surface, SKILL serving, /admin/manifest, and /admin/capabilities will
#      be wired in Day 3 of the v0.1.29 refactor.
#   2. Future extraction to a shared package is a move, not a rewrite. When
#      this class gets lifted into its own library, downstream apps don't need
#      to change their inheritance chain.
#
# Inheritance chain after Day 1b:
#   Serverless__Fast_API → Agentic_FastAPI → Fast_API__Playwright__Service
#
# Day 3 will add:
#   • Agentic_Admin_API mount at /admin/*
#   • SKILL file serving
#   • /admin/manifest + /admin/capabilities
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                        import Serverless__Fast_API


class Agentic_FastAPI(Serverless__Fast_API):
    pass                                                                            # Empty on purpose — admin surface lands in Day 3 of v0.1.29
