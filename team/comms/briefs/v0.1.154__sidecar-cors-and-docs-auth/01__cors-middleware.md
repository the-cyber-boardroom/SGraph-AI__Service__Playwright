# CORS Middleware

## Where to add it

`sg_compute/host_plane/fast_api/Fast_API__Host__Control.py` — in the method that
builds / returns the FastAPI `app` instance.

## What to add

```python
from starlette.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],        # sidecar is on a private EC2; open is fine
    allow_methods     = ["*"],
    allow_headers     = ["*"],
    allow_credentials = False,
)
```

`allow_credentials = False` is intentional — credentials (cookies/auth) are passed
via the `X-API-Key` header which is covered by `allow_headers = ["*"]`, not by the
credentials flag.

## Why `allow_origins = ["*"]`

The sidecar is bound to a public EC2 IP but protected by `X-API-Key` auth on every
endpoint. The CORS wildcard only controls which browser origins can READ the
response — the API key is still required to actually get data. Locking down origins
would require knowing the admin dashboard URL at deploy time, which varies per
environment.

## Test expectation

After adding the middleware, a preflight OPTIONS from the browser:
```
OPTIONS http://13.40.49.210:19009/pods/list
Origin: http://localhost:10071
Access-Control-Request-Headers: X-API-Key
```
must receive:
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Methods: *
```

Existing test file: `sg_compute__tests/host_plane/fast_api/test_Fast_API__Host__Control.py`
— add a test that does an OPTIONS preflight and checks the response headers.
