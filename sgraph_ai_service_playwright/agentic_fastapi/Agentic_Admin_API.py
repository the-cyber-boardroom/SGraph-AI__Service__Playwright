# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_Admin_API — /admin/* surface (v0.1.29)
#
# Read-only framework introspection routes mounted under /admin/ by
# Agentic_FastAPI. Every response is a Type_Safe schema; no raw dicts escape.
#
# Routes (tag 'admin', prefix '/admin'):
#   GET /admin/health         -> Schema__Agentic__Health        — status + code_source
#   GET /admin/info           -> Schema__Agentic__Info          — app_name, stage, version, image_version, code_source, python
#   GET /admin/env            -> Schema__Agentic__Env           — redacted to AGENTIC_* only
#   GET /admin/boot-log       -> Schema__Agentic__Boot_Log      — last N lines from Agentic_Boot_State
#   GET /admin/error          -> Schema__Agentic__Error         — last boot error (empty on happy path)
#   GET /admin/skills/{name}  -> Schema__Agentic__Skill         — raw markdown for human / browser / agent
#   GET /admin/manifest       -> Schema__Agentic__Manifest      — openapi + capabilities + skills entry points
#   GET /admin/capabilities   -> Schema__Agentic__Capabilities  — wire-typed capabilities.json
#
# Two configurable paths (resolved by Agentic_FastAPI at setup time and passed
# in as attributes):
#
#   • skills_dir        — folder with skill__{name}.md files.
#   • capabilities_path — absolute path to capabilities.json.
#
# /admin/reload is deferred per plan §5 (needs auth + AGENTIC_ADMIN_MODE=full).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys

from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous import Safe_Str__Text__Dangerous

from sgraph_ai_service_playwright.agentic_fastapi.Agentic_Boot_State                import (get_boot_log,
                                                                                            get_last_error)
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Boot_Log import Schema__Agentic__Boot_Log
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Capabilities import Schema__Agentic__Capabilities
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Env     import Schema__Agentic__Env
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Error   import Schema__Agentic__Error
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Health  import Schema__Agentic__Health
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Info    import Schema__Agentic__Info
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Manifest import Schema__Agentic__Manifest
from sgraph_ai_service_playwright.agentic_fastapi.schemas.Schema__Agentic__Skill   import Schema__Agentic__Skill
from sgraph_ai_service_playwright.consts.env_vars                                  import (ENV_VAR__AGENTIC_APP_NAME    ,
                                                                                           ENV_VAR__AGENTIC_APP_STAGE   ,
                                                                                           ENV_VAR__AGENTIC_APP_VERSION ,
                                                                                           ENV_VAR__AGENTIC_CODE_SOURCE ,
                                                                                           ENV_VAR__AGENTIC_IMAGE_VERSION)


TAG__ROUTES_ADMIN          = 'admin'
AGENTIC_ENV_PREFIX         = 'AGENTIC_'                                             # /admin/env includes only keys starting with this prefix
SKILL_FILENAME_FORMAT      = 'skill__{name}.md'
DEFAULT_OPENAPI_PATH       = '/openapi.json'
DEFAULT_CAPABILITIES_PATH  = '/admin/capabilities'
SKILL_NAMES                = ['human', 'browser', 'agent']                          # First-pass set per plan §6 — enumerated in /admin/manifest


class Agentic_Admin_API(Fast_API__Routes):
    tag               : str                      = TAG__ROUTES_ADMIN
    skills_dir        : Safe_Str__Text__Dangerous                                   # Absolute path to the folder holding skill__*.md
    capabilities_path : Safe_Str__Text__Dangerous                                   # Absolute path to capabilities.json on disk

    # ── /admin/health ─────────────────────────────────────────────────────────
    def health(self) -> Schema__Agentic__Health:                                    # Always 200; the status field tells the story
        status = 'degraded' if get_last_error() else 'loaded'
        return Schema__Agentic__Health(status      = status,
                                       code_source = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE, ''))

    # ── /admin/info ───────────────────────────────────────────────────────────
    def info(self) -> Schema__Agentic__Info:
        return Schema__Agentic__Info(app_name       = os.environ.get(ENV_VAR__AGENTIC_APP_NAME     , ''      ),
                                     app_stage      = os.environ.get(ENV_VAR__AGENTIC_APP_STAGE    , ''      ),
                                     app_version    = os.environ.get(ENV_VAR__AGENTIC_APP_VERSION  , 'v0'    ),  # Safe_Str__Version rejects empty; 'v0' is the documented fallback sentinel
                                     image_version  = os.environ.get(ENV_VAR__AGENTIC_IMAGE_VERSION, 'v0'    ),
                                     code_source    = os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE  , ''      ),
                                     python_version = sys.version)

    # ── /admin/env (redacted) ─────────────────────────────────────────────────
    def env(self) -> Schema__Agentic__Env:                                          # Only AGENTIC_* — never leaks AWS creds or auth tokens
        redacted = {k: v for k, v in os.environ.items() if k.startswith(AGENTIC_ENV_PREFIX)}
        return Schema__Agentic__Env(agentic_vars=redacted)

    # ── /admin/boot-log ───────────────────────────────────────────────────────
    def boot_log(self) -> Schema__Agentic__Boot_Log:
        return Schema__Agentic__Boot_Log(lines=get_boot_log())

    # ── /admin/error ──────────────────────────────────────────────────────────
    def error(self) -> Schema__Agentic__Error:
        last = get_last_error()
        return Schema__Agentic__Error(has_error=bool(last), error=last)

    # ── /admin/skills/{name} ──────────────────────────────────────────────────
    def skills__name(self, name: str) -> Schema__Agentic__Skill:                    # Double-underscore splits to /skills/{name} — path param parsed by Fast_API__Route__Parser
        if name not in SKILL_NAMES:                                                 # Keep the allow-list tight; unknown names must 404, not crash
            from fastapi                                                                        import HTTPException
            raise HTTPException(status_code=404, detail=f'unknown skill: {name}')
        skill_path = os.path.join(str(self.skills_dir), SKILL_FILENAME_FORMAT.format(name=name))
        if not os.path.isfile(skill_path):
            from fastapi                                                                        import HTTPException
            raise HTTPException(status_code=404, detail=f'skill file missing: {skill_path}')
        with open(skill_path, 'r') as f:
            content = f.read()
        return Schema__Agentic__Skill(name=name, content=content)

    # ── /admin/manifest ───────────────────────────────────────────────────────
    def manifest(self) -> Schema__Agentic__Manifest:                                # Single entry point for agent discovery — points at OpenAPI + SKILLs + capabilities
        skills = {name: f'/{TAG__ROUTES_ADMIN}/skills/{name}' for name in SKILL_NAMES}
        return Schema__Agentic__Manifest(app_name          = os.environ.get(ENV_VAR__AGENTIC_APP_NAME, ''),
                                         openapi_path      = DEFAULT_OPENAPI_PATH      ,
                                         capabilities_path = DEFAULT_CAPABILITIES_PATH ,
                                         skills            = skills                    )

    # ── /admin/capabilities ───────────────────────────────────────────────────
    def capabilities(self) -> Schema__Agentic__Capabilities:                        # Wire-typed mirror of repo-root capabilities.json
        with open(str(self.capabilities_path), 'r') as f:
            data = json.load(f)
        return Schema__Agentic__Capabilities(app                = data.get('app'               , ''  ),
                                             version            = data.get('version'           , 'v0'),
                                             axioms             = data.get('axioms'            , [] ),
                                             declared_narrowing = data.get('declared_narrowing', [] ))

    def setup_routes(self):
        self.add_route_get(self.health        )
        self.add_route_get(self.info          )
        self.add_route_get(self.env           )
        self.add_route_get(self.boot_log      )
        self.add_route_get(self.error         )
        self.add_route_get(self.skills__name  )
        self.add_route_get(self.manifest      )
        self.add_route_get(self.capabilities  )
