# ═══════════════════════════════════════════════════════════════════════════════
# Agentic Lambda entry point (v0.1.29 — thin shim over Agentic_Boot_Shim)
#
# Lives INSIDE the container image (copied to /var/task/lambda_entry.py) and is
# the Lambda entry point. Delegates ALL boot logic to
# sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim, which
# in turn delegates code resolution to Agentic_Code_Loader. Kept tiny so the
# file that's baked into the image is dumb — the interesting code lives in
# the package, which is also what gets hot-swapped.
#
# Tests that `import lambda_entry` get no side effects — boot() only fires
# inside main() or run(), never at module import.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim             import Agentic_Boot_Shim


error        = None
handler      = None
app          = None
code_source  = None


def main():                                                                         # Invoked by the Dockerfile CMD (and the __main__ block below)
    global error, handler, app, code_source
    error, handler, app, code_source = Agentic_Boot_Shim().boot()
    if error:
        raise RuntimeError(error)
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))


def run(event, context=None):                                                       # Direct Lambda handler entry (non-LWA mode) — boots on first call
    global error, handler, app, code_source
    if handler is None and error is None:
        error, handler, app, code_source = Agentic_Boot_Shim().boot()
    if error:
        return error
    return handler(event, context)


if __name__ == '__main__':
    main()
