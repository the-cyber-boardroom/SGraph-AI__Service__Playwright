# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright Service — lambda_handler
#
# Boots the FastAPI app under uvicorn (port 8000) for AWS Lambda Web Adapter.
# The `sys.path.append('/opt/python')` workaround is carried forward from
# OSBot-Playwright — LWA loses the path to Lambda layers on cold start.
#
# The service class (`Fast_API__Playwright__Service`) is imported lazily inside
# `run()` so the module is importable without side effects (required for tests).
# ═══════════════════════════════════════════════════════════════════════════════

import sys

sys.path.append('/opt/python')                                                   # LWA workaround — preserve layer path


def run():
    # Lazy import — keeps module importable without starting uvicorn or loading FastAPI.
    from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service

    import uvicorn

    fast_api_service = Fast_API__Playwright__Service().setup()
    app              = fast_api_service.app()
    uvicorn.run(app, host='0.0.0.0', port=8000)


if __name__ == '__main__':
    run()
