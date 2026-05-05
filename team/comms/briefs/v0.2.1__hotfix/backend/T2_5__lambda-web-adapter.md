# T2.5 — Replace Mangum with AWS Lambda Web Adapter (or document the deviation)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

`sg_compute/control_plane/lambda_handler.py` (BV2.5) uses **Mangum** to wrap the FastAPI app for Lambda. The project stack table in `.claude/CLAUDE.md` is explicit:

> **Lambda adapter** — AWS Lambda Web Adapter 1.0.0
>
> **Web framework** — FastAPI via `Serverless__Fast_API`
>
> Lambda Web Adapter — HTTP translation, **not Mangum**

Same constraint applied to BV6's `host_plane/fast_api/lambda_handler.py` — verify if it also uses Mangum (it likely does, for consistency).

## Tasks

1. **Read `.claude/CLAUDE.md`** — confirm the Lambda Web Adapter rule.
2. **Two options**:
   - Option A — switch to Lambda Web Adapter. The adapter wraps the running FastAPI process (no Python wrapper code needed); the Dockerfile installs the adapter binary via the `aws-lambda-web-adapter` extension layer. The `lambda_handler.py` becomes essentially empty (or removed; the entry point is `uvicorn`).
   - Option B — document why Mangum was kept. If there's a real reason (e.g. the host_plane Lambda doesn't have CloudFront in front), file an Architect review and amend the rule.
3. **Recommended: Option A.** Mangum has known compatibility issues with newer FastAPI versions; the project's existing host-control image already supports the Web Adapter pattern.
4. **Update Dockerfile** — `docker/control-plane/Dockerfile` (or wherever the control plane is built). Add the Web Adapter extension layer.
5. **Test** — the Lambda boots, serves `/api/health`, handles concurrent requests.

## Acceptance criteria

- `lambda_handler.py` no longer imports Mangum (Option A) OR an Architect-ratified deviation note exists in the architecture doc (Option B).
- Lambda smoke test passes from the new wrapper.
- `host_plane/fast_api/lambda_handler.py` uses the same approach (consistency).

## Live smoke test

`curl <lambda-url>/api/health` → 200. Concurrent loadgen — no Mangum-specific failures (e.g. lifespan issues).

## Source

Executive review Tier-2; backend-early review §"Top contract violation #2".
