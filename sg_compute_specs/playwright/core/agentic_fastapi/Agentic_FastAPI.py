# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_FastAPI — L1 base class (v0.1.29, first-pass agentic refactor)
#
# Generic FastAPI base that every "agentic" app extends. Mounts the shared
# /admin/* surface (via Agentic_Admin_API) on every subclass so that a newly
# declared agentic app gets self-describing health / info / manifest / SKILL
# endpoints for free.
#
# Inheritance chain:
#   Serverless__Fast_API → Agentic_FastAPI → Fast_API__Playwright__Service
#
# App subclasses that override setup_routes() MUST call super().setup_routes()
# so the admin surface lands. The two `resolve_*` hooks let subclasses override
# where the app keeps its SKILL files and capabilities.json; the defaults
# satisfy the in-tree Playwright layout (app package sibling to lambda_entry).
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_fast_api.api.schemas.consts.consts__Fast_API                             import AUTH__EXCLUDED_PATHS
from osbot_fast_api_serverless.fast_api.Serverless__Fast_API                        import Serverless__Fast_API

from sg_compute_specs.playwright.core.agentic_fastapi.Agentic_Admin_API                 import (Agentic_Admin_API,
                                                                                            SKILL_NAMES       ,
                                                                                            TAG__ROUTES_ADMIN )


# Default filesystem locations — resolvable from any process that has the
# app package on sys.path. Subclasses override resolve_* when they ship in
# a different layout (extracted package, different zip layout, etc.).
_THIS_DIR                 = os.path.dirname(os.path.abspath(__file__))
_APP_PACKAGE_DIR          = os.path.dirname(_THIS_DIR)                              # sgraph_ai_service_playwright/
_REPO_ROOT_GUESS          = os.path.dirname(_APP_PACKAGE_DIR)                       # Repo root (sibling to the app package)

DEFAULT_SKILLS_DIR        = os.path.join(_APP_PACKAGE_DIR, 'skills')                # sgraph_ai_service_playwright/skills/
DEFAULT_CAPABILITIES_PATH = os.path.join(_REPO_ROOT_GUESS, 'capabilities.json')     # Repo-root sibling to lambda_entry.py

# Public admin paths bypass the API-key middleware. The admin surface is
# read-only and /admin/env already redacts to AGENTIC_* only, so there is no
# secret on these endpoints. /admin/reload (deferred; needs auth) will NOT be
# listed here when it lands.
ADMIN_AUTH_EXCLUDED_PATHS = [f'/{TAG__ROUTES_ADMIN}/health'       ,
                             f'/{TAG__ROUTES_ADMIN}/info'         ,
                             f'/{TAG__ROUTES_ADMIN}/env'          ,
                             f'/{TAG__ROUTES_ADMIN}/boot-log'     ,
                             f'/{TAG__ROUTES_ADMIN}/error'        ,
                             f'/{TAG__ROUTES_ADMIN}/manifest'     ,
                             f'/{TAG__ROUTES_ADMIN}/capabilities' ,
                             *(f'/{TAG__ROUTES_ADMIN}/skills/{name}' for name in SKILL_NAMES)]


class Agentic_FastAPI(Serverless__Fast_API):

    def resolve_skills_dir(self) -> str:                                            # Override in subclasses shipped outside this repo layout
        return DEFAULT_SKILLS_DIR

    def resolve_capabilities_path(self) -> str:
        lambda_baked = '/var/task/capabilities.json'                                # Baked into the image by the Dockerfile; preferred when present
        if os.path.isfile(lambda_baked):
            return lambda_baked
        return DEFAULT_CAPABILITIES_PATH

    def setup(self):                                                                # Extend AUTH__EXCLUDED_PATHS before middlewares run; once per class lifetime
        for path in ADMIN_AUTH_EXCLUDED_PATHS:
            if path not in AUTH__EXCLUDED_PATHS:
                AUTH__EXCLUDED_PATHS.append(path)
        return super().setup()

    def setup_routes(self):                                                         # Subclasses override and MUST call super().setup_routes() — app + admin
        super().setup_routes()                                                      # Serverless__Fast_API adds its /info route group
        self.add_routes(Agentic_Admin_API,
                        skills_dir        = self.resolve_skills_dir()        ,
                        capabilities_path = self.resolve_capabilities_path() )
