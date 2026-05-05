# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Agentic_FastAPI (v0.1.29)
#
# Day 1b scope: the base class exists and is an importable passthrough over
# Serverless__Fast_API. Admin routes land in Day 3 — no route assertions here.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                        import Serverless__Fast_API

from sg_compute_specs.playwright.core.agentic_fastapi.Agentic_FastAPI                   import Agentic_FastAPI


class test_Agentic_FastAPI(TestCase):

    def test__is_subclass_of_serverless_fast_api(self):
        assert issubclass(Agentic_FastAPI, Serverless__Fast_API)

    def test__playwright_service_extends_it(self):                                  # Inheritance chain: Serverless__Fast_API → Agentic_FastAPI → Fast_API__Playwright__Service
        from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service
        assert issubclass(Fast_API__Playwright__Service, Agentic_FastAPI)
