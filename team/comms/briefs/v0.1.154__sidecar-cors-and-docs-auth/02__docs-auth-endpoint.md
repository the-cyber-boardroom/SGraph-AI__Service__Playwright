# `/docs-auth` Endpoint

## Purpose

Serves a Swagger UI page with the host API key pre-injected as a
`requestInterceptor`. The UI loads this in an iframe — the iframe origin is the
sidecar itself, so `/openapi.json` and all API calls are same-origin (no CORS
needed for Swagger to work).

The user clicks Execute in Swagger and the call goes through authenticated,
with zero manual steps.

## Endpoint spec

```
GET /docs-auth?apikey={host_api_key}
```

- Not included in the OpenAPI schema (`include_in_schema=False`)
- Returns `text/html`
- `apikey` query param is optional — if missing, serves standard Swagger without auth injection
- No authentication required on this endpoint itself (it only serves static HTML)

## Implementation

Add to `Routes__Host__Status` or a new `Routes__Host__Docs` class, or directly on
`Fast_API__Host__Control` as an exception handler / raw route.

Minimal HTML template (the backend controls the template, adjust styling as needed):

```python
import json
from fastapi import Query
from fastapi.responses import HTMLResponse

DOCS_AUTH_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Fast_API__Host__Control — Docs</title>
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

@app.get("/docs-auth", include_in_schema=False)
async def docs_auth(apikey: str = Query(default="")):
    html = DOCS_AUTH_TEMPLATE.format(api_key_json=json.dumps(apikey))
    return HTMLResponse(content=html)
```

`json.dumps(apikey)` produces a properly JSON-escaped string literal — safe against
injection even if the key contains quotes or backslashes.

## How the UI uses it

```javascript
// sp-cli-host-api-panel.js
const docsUrl = key
    ? `${url}/docs-auth?apikey=${encodeURIComponent(key)}`
    : `${url}/docs`
this._frame.src = docsUrl
```

The iframe is already wired to this URL. Once this endpoint is deployed, Swagger
Execute calls will be authenticated with no user interaction.

## Security note

The API key appears in the query string of the iframe URL. This is acceptable
because:
1. All admin dashboard access already requires the SP CLI management API key
2. The sidecar is on a non-public port (19009) on an EC2 instance
3. The key is already stored in localStorage (same exposure level)
4. HTTPS will encrypt it in transit once TLS is added to the sidecar

If this is a concern, an alternative is a `POST /docs-auth` with the key in the
body, but that complicates the iframe loading pattern.

## Acceptance test

```python
def test_docs_auth__returns_html_with_key():
    resp = test_client.get('/docs-auth?apikey=test-key-abc')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers['content-type']
    assert '"test-key-abc"' in resp.text          # key JSON-encoded in the page
    assert 'X-API-Key' in resp.text               # used as the header name
    assert 'requestInterceptor' in resp.text

def test_docs_auth__no_key():
    resp = test_client.get('/docs-auth')
    assert resp.status_code == 200
    assert '""' in resp.text    # empty string for apiKey
```
