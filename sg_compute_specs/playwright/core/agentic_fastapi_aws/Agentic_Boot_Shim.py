# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_Boot_Shim — generic Lambda boot orchestration (v0.1.29+)
#
# Invoked by an app-specific `lambda_entry.py` at container start. Three stages,
# each surfaced as a discrete method so tests can exercise them in isolation:
#
#   1. read_image_version()  — reads /var/task/image_version baked by the
#                              Dockerfile; writes to AGENTIC_IMAGE_VERSION so
#                              the owning app can surface it on /info.
#   2. Agentic_Code_Loader.resolve()
#                            — local path > S3 > passthrough; mutates sys.path.
#   3. boot()                — dynamically imports the user FastAPI class (via
#                              `fast_api_class_path`), runs .setup(), pins
#                              (handler, app). On failure inside Lambda we
#                              catch and return an error string so the client
#                              sees something other than "empty body". Outside
#                              Lambda we re-raise so dev loops get a stack
#                              trace.
#
# Generic by design: no app knowledge is hardcoded. Every consumer passes its
# own `fast_api_class_path` ("module.submodule.ClassName") and an optional
# `service_label` used in error messages. The shim stays one file, one class,
# reused across every Lambda that wants S3-hot-swap semantics.
#
# The shim is BAKED into the container image, never hot-swapped. It's the
# rollback escape hatch: if the zip is unloadable the image is still there.
# Once Agentic_Code_Loader prepends /tmp/agentic-code/.../<package> to
# sys.path, subsequent imports of the package go to the S3 copy — but this
# shim has already been imported by then, so its own code is pinned to the
# baked version. OK for first boot; warm invocations don't re-run the shim.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import os

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.playwright.core.agentic_fastapi.Agentic_Boot_State                import (append_boot_log ,
                                                                                            set_last_error  )
from sg_compute_specs.playwright.core.agentic_fastapi_aws.Agentic_Code_Loader           import Agentic_Code_Loader
from sg_compute_specs.playwright.core.consts.env_vars                                   import (ENV_VAR__AGENTIC_CODE_SOURCE  ,
                                                                                            ENV_VAR__AGENTIC_IMAGE_VERSION)


IMAGE_VERSION_PATH       = '/var/task/image_version'                                # Baked at build time by the Dockerfile
FALLBACK_IMAGE_VERSION   = 'v0'                                                     # Matches Safe_Str__Version regex — "unknown / pre-v0.1.28"
ENV_VAR__LAMBDA_FUNCTION = 'AWS_LAMBDA_FUNCTION_NAME'                               # Set by AWS; absence means we're not on Lambda
DEFAULT_SERVICE_LABEL    = 'service'                                                # Cosmetic — appears in the boot-failure error message


class Agentic_Boot_Shim(Type_Safe):
    fast_api_class_path : str = ''                                                  # e.g. 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service.Fast_API__Playwright__Service'
    service_label       : str = DEFAULT_SERVICE_LABEL                               # e.g. 'Playwright service' or 'SP CLI service'

    def read_image_version(self) -> str:                                            # Best-effort — missing file means local dev / non-Lambda
        if os.path.exists(IMAGE_VERSION_PATH):
            with open(IMAGE_VERSION_PATH, 'r') as f:
                return f.read().strip()
        return FALLBACK_IMAGE_VERSION

    def resolve_fast_api_class(self):                                               # Dynamically import the configured class path; raise on misconfiguration
        if not self.fast_api_class_path:
            raise RuntimeError('Agentic_Boot_Shim.fast_api_class_path is empty — '
                               'pass it when instantiating (e.g. '
                               "Agentic_Boot_Shim(fast_api_class_path='pkg.mod.ClassName'))")
        module_path, separator, class_name = self.fast_api_class_path.rpartition('.')
        if not separator or not module_path or not class_name:
            raise RuntimeError(f'fast_api_class_path must be fully qualified '
                               f'(module.submodule.ClassName): {self.fast_api_class_path!r}')
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def boot(self):                                                                 # Stage 2+3 — import + setup; returns (error, handler, app, code_source)
        image_version = self.read_image_version()
        os.environ.setdefault(ENV_VAR__AGENTIC_IMAGE_VERSION, image_version)
        append_boot_log(f'image_version={image_version}')

        code_source = Agentic_Code_Loader().resolve()
        os.environ[ENV_VAR__AGENTIC_CODE_SOURCE] = code_source                      # Surfaced in /health/info — "s3:…", "local:…", or "passthrough:sys.path"
        append_boot_log(f'code_source={code_source}')

        try:
            fa_class = self.resolve_fast_api_class()
            fa       = fa_class().setup()
            handler  = fa.handler()
            app      = fa.app()
            append_boot_log('status=loaded')
            set_last_error('')                                                      # Clear any prior-cold-start error on warm success
            return None, handler, app, code_source
        except Exception as exc:
            error = (f"CRITICAL ERROR: Failed to start {self.service_label}:\n\n"
                     f"{type(exc).__name__}: {exc}\n\n"
                     f"code_source: {code_source}")
            append_boot_log(f'status=degraded error={type(exc).__name__}: {exc}')
            set_last_error(error)
            if not os.environ.get(ENV_VAR__LAMBDA_FUNCTION):                        # Outside Lambda, stack trace > string — fail loud
                raise
            return error, None, None, code_source
