# ═══════════════════════════════════════════════════════════════════════════════
# Playwright service — Lambda entry point (v0.1.29+ — generic-shim consumer)
#
# Lives INSIDE the container image (copied to /var/task/lambda_entry.py) and is
# the Lambda entry point. Delegates ALL boot logic to
# sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim — which
# is now generic (no hardcoded app import). This file is the Playwright
# service's adapter: it pins the FastAPI class path + service label passed
# into the shim. Sibling apps (e.g. sp-playwright-cli) provide their own
# lambda_entry with their own class path.
#
# Tests that `import lambda_entry` get no side effects — boot() only fires
# inside main() or run(), never at module import.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim             import Agentic_Boot_Shim


PLAYWRIGHT_FAST_API_CLASS_PATH = 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service.Fast_API__Playwright__Service'
PLAYWRIGHT_SERVICE_LABEL       = 'Playwright service'


def build_shim() -> Agentic_Boot_Shim:                                              # Exposed so tests can assert the wiring without invoking boot()
    return Agentic_Boot_Shim(fast_api_class_path = PLAYWRIGHT_FAST_API_CLASS_PATH ,
                             service_label       = PLAYWRIGHT_SERVICE_LABEL        )


error        = None
handler      = None
app          = None
code_source  = None


def main():                                                                         # Invoked by the Dockerfile CMD (and the __main__ block below)
    global error, handler, app, code_source
    error, handler, app, code_source = build_shim().boot()
    if error:
        raise RuntimeError(error)
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))


def run(event, context=None):                                                       # Direct Lambda handler entry (non-LWA mode) — boots on first call
    global error, handler, app, code_source
    if handler is None and error is None:
        error, handler, app, code_source = build_shim().boot()
    if error:
        return error
    return handler(event, context)


if __name__ == '__main__':
    main()
