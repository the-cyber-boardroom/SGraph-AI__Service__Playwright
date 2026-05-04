# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Docs
#
# GET /docs-auth?apikey={key}
#   Serves Swagger UI with the host API key pre-injected as a requestInterceptor.
#   The UI loads this in an iframe — iframe origin is the sidecar, so /openapi.json
#   is same-origin and no CORS is needed for Swagger itself to work.
#   Registered at root (prefix='/') to match /docs and /redoc convention.
#   Not included in the OpenAPI schema (hidden from the Swagger UI itself).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from fastapi                                                                    import Query
from fastapi.responses                                                          import HTMLResponse
from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix     import Safe_Str__Fast_API__Route__Prefix


TAG__ROUTES_HOST_DOCS = 'host'

DOCS_AUTH_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Host Control — API Docs</title>
  <link rel="stylesheet"
        href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    body {{ margin: 0; }}
    .topbar {{ display: none !important; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    const apiKey = {api_key_json};
    SwaggerUIBundle({{
      url:             '/openapi.json',
      dom_id:          '#swagger-ui',
      presets:         [SwaggerUIBundle.presets.apis],
      tryItOutEnabled: true,
      persistAuthorization: true,
      requestInterceptor: function(req) {{
        if (apiKey) req.headers['X-API-Key'] = apiKey;
        return req;
      }},
    }});
  </script>
</body>
</html>"""


class Routes__Host__Docs(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_DOCS

    def setup_routes(self):
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')
        router = self.router

        @router.get('/docs-auth', include_in_schema=False)
        async def docs_auth(apikey: str = Query(default="")):
            html = DOCS_AUTH_TEMPLATE.format(api_key_json=json.dumps(apikey))
            return HTMLResponse(content=html)
