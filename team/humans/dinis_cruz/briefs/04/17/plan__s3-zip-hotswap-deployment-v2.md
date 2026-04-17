# S3-Zip Hot-Swap Code Deployment — Implementation Plan (v2)

**Goal:** decouple the Playwright service's code from the Docker image. Deploy new code in seconds (S3 upload) instead of minutes (image rebuild + ECR push). Run the same image locally by pointing the container at a local code source.

**Reference spec:** `initial-brief/dev-specs/base-image-research.md` §162–202 (Pattern B).
**Reference pattern:** `sgraph_ai_app_send.lambda__user.*` — Dinis's established osbot pattern.
**Packaging primitives:** `osbot_utils.helpers.Zip_Bytes`, `osbot_aws.aws.s3.S3__Zip_Bytes`.

---

## Key clarifications from Dinis's existing pattern

1. **No separate fallback service.** A top-level try/catch at module import time pins `error`/`handler`/`app` — if setup fails, `run()` returns the critical error as the response body. Much simpler than a parallel health-check app.

2. **Dependencies are already in the image** for the Playwright service (Playwright + FastAPI + boto3 + Chromium). `load_dependencies` pattern is NOT needed here — we only need code loading.

3. **S3 layout follows Dinis's convention:**
   - Bucket: `{account_id}--sg-playwright--{region_name}` (one bucket, similar to `osbot-lambdas` convention)
   - Folder per Lambda name: `s3://.../sg-playwright-dev/`
   - Versioned zips: `s3://.../sg-playwright-dev/code/v0.1.28.zip` (CI-controlled version)
   - `latest.zip` pointer: `s3://.../sg-playwright-dev/code/latest.zip`

4. **`AWS_REGION` check is the "am I on Lambda?" gate** — outside Lambda, skip the S3 download and fall through to whatever's on `sys.path` already (mounted volume or container-baked fallback).

---

## The Contract — four env vars

| Env var | Purpose | Example |
|---|---|---|
| `SG_PLAYWRIGHT__LAMBDA_NAME` | Lambda name — maps to the S3 folder | `sg-playwright-dev` |
| `SG_PLAYWRIGHT__CODE_S3_VERSION` | Version to load, or `latest` | `v0.1.28` or `latest` |
| `SG_PLAYWRIGHT__CODE_LOCAL_PATH` | Override: use this local path instead of S3 | `/mnt/code` |
| `AWS_REGION` | Set by Lambda automatically; absent locally | `eu-west-2` |

**Decision logic (precedence order):**

```
if SG_PLAYWRIGHT__CODE_LOCAL_PATH is set:
    sys.path.insert(0, it)  # laptop or volume-mounted local dev
elif AWS_REGION is set:
    download s3://<acct>--sg-playwright--<region>/<lambda_name>/code/<version>.zip
    extract to /tmp/sg-playwright-code/<version>
    sys.path.insert(0, that path)
else:
    no-op — whatever is already on sys.path wins (tests, local uvicorn with PYTHONPATH set)
```

Three cases:
- **Lambda:** `AWS_REGION` set, no local path → downloads from S3
- **Local Docker with mounted code:** `SG_PLAYWRIGHT__CODE_LOCAL_PATH=/mnt/code` → uses mount directly, zero download
- **Local pytest / IDE:** neither set → `PYTHONPATH` or editable install handles it

---

## Implementation

### The boot loader — `lambda_entry.py` at Lambda handler root

Following Dinis's existing pattern almost verbatim, adapted for code loading (not dependencies):

```python
# lambda_entry.py  —  Lambda handler entry point; lives INSIDE the container image
# Loaded by AWS Lambda runtime or invoked manually for local testing.
import os

# ─── Stage 1: resolve code source, mutate sys.path BEFORE importing the app ───

def load_code_from_s3():
    """Download the versioned code zip from S3 and prepend to sys.path.
    Only runs inside Lambda (AWS_REGION is set). No-op otherwise."""
    if os.getenv('AWS_REGION') is None:
        return None
    if os.getenv('SG_PLAYWRIGHT__CODE_LOCAL_PATH'):           # local override wins
        return None

    import boto3, zipfile, sys, io

    lambda_name = os.environ['SG_PLAYWRIGHT__LAMBDA_NAME']
    version     = os.environ.get('SG_PLAYWRIGHT__CODE_S3_VERSION', 'latest')

    sts         = boto3.client('sts')
    account_id  = sts.get_caller_identity()['Account']
    region_name = boto3.session.Session().region_name
    bucket_name = f'{account_id}--sg-playwright--{region_name}'
    s3_key      = f'{lambda_name}/code/{version}.zip'
    target_dir  = f'/tmp/sg-playwright-code/{lambda_name}/{version}'

    os.makedirs(target_dir, exist_ok=True)

    # Cold-start optimisation: if target_dir is already populated and the
    # S3 ETag matches what we previously cached, skip re-download.
    # (implementation detail — can ship initially without this)

    s3        = boto3.client('s3')
    response  = s3.get_object(Bucket=bucket_name, Key=s3_key)
    zip_bytes = response['Body'].read()

    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    sys.path.insert(0, target_dir)
    return f's3://{bucket_name}/{s3_key} → {target_dir}'


def load_code_from_local_path():
    """Use SG_PLAYWRIGHT__CODE_LOCAL_PATH directly — for local Docker runs
    with a volume mount. No download, no extract, just sys.path."""
    import sys
    local_path = os.getenv('SG_PLAYWRIGHT__CODE_LOCAL_PATH')
    if not local_path:
        return None
    if not os.path.isdir(local_path):
        raise RuntimeError(f'SG_PLAYWRIGHT__CODE_LOCAL_PATH does not exist or is not a directory: {local_path}')
    sys.path.insert(0, local_path)
    return f'local path: {local_path}'


def clear_osbot_aws_modules():
    """After load_code_from_s3 runs, purge the boto3-only osbot_aws footprint
    so the real sgraph_ai_service_playwright code (which may use a different
    osbot_aws version bundled in the zip) isn't shadowed."""
    import sys
    for module in list(sys.modules):
        if module.startswith('osbot_aws'):
            del sys.modules[module]


# ─── Stage 2: load code (S3 OR local mount) ───────────────────────────────────

code_source = load_code_from_local_path() or load_code_from_s3()
clear_osbot_aws_modules()

# ─── Stage 3: import + construct the app, pinning error/handler/app ─────────

error   = None
handler = None
app     = None

try:
    from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service import Fast_API__Playwright__Service

    with Fast_API__Playwright__Service() as _:
        _.setup()
        handler = _.handler()
        app     = _.app()
except Exception as exc:
    # Outside Lambda, fail loudly — developer wants the stack trace, not a string.
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is None:
        raise
    error = (f"CRITICAL ERROR: Failed to start service with:\n\n"
             f"{type(exc).__name__}: {exc}\n\n"
             f"code_source: {code_source}")


def run(event, context=None):
    if error:
        return error
    return handler(event, context)
```

**Note:** this is a single file that ships inside the container image. It's the Lambda handler entry point. It replaces the current `sgraph_ai_service_playwright.main:app` that uvicorn imports — the LWA path can be rewired to invoke `lambda_entry.run` instead, OR uvicorn can import `lambda_entry:app` and the same file serves both modes.

### CI: packaging the code zip

Two new pieces, both thin:

**`scripts/package_code.py`** — builds the zip, uploads to S3, updates `latest.zip`:

```python
# Run in CI after version bump. Uses osbot-aws primitives.
from osbot_aws.aws.s3.S3__Zip_Bytes import S3__Zip_Bytes
from osbot_aws.aws.s3.S3 import S3
import boto3, os

def deploy_code(lambda_name: str, version: str):
    sts         = boto3.client('sts')
    account_id  = sts.get_caller_identity()['Account']
    region_name = boto3.session.Session().region_name
    bucket_name = f'{account_id}--sg-playwright--{region_name}'
    s3_prefix   = f'{lambda_name}/code'

    # Package the entire service package
    zb = S3__Zip_Bytes(s3=S3())
    zb.add_folder__from_disk('sgraph_ai_service_playwright', r'.*\.py$')

    # Versioned zip
    versioned_key = f'{s3_prefix}/{version}.zip'
    zb.save_to_s3(bucket_name, versioned_key)

    # Latest pointer — same bytes, just a second key
    latest_key = f'{s3_prefix}/latest.zip'
    zb.save_to_s3(bucket_name, latest_key)

    print(f'uploaded {len(zb.zip_bytes):,} bytes to:')
    print(f'  s3://{bucket_name}/{versioned_key}')
    print(f'  s3://{bucket_name}/{latest_key}')
    return {'versioned': versioned_key, 'latest': latest_key}

if __name__ == '__main__':
    lambda_name = os.environ['LAMBDA_NAME']          # sg-playwright-dev
    version     = open('sgraph_ai_service_playwright/version').read().strip()
    deploy_code(lambda_name, version)
```

**Lambda recycle trigger** — bump an env var to force container refresh on next cold start:

```python
from osbot_aws.aws.lambda_.Lambda import Lambda

fn = Lambda(name=lambda_name)
current = fn.function_configuration().get('Environment', {}).get('Variables', {})
fn.env_variables = {**current, 'SG_PLAYWRIGHT__CODE_S3_VERSION': version}
fn.update_lambda_configuration()
```

### CI pipeline split

**Track A — runtime image (changes rarely):**
- Build Docker image
- Push to ECR
- Bump `IMAGE_VERSION` tag on the Lambda config (image version is separate from code version)
- Trigger: changes to `Dockerfile`, `requirements.txt`, `bootloader/`, `lambda_entry.py`

**Track B — code deploy (every commit):**
- Unit tests
- Version bump (existing logic — CI already does this)
- `scripts/package_code.py`
- Update Lambda env var to force recycle
- Smoke test
- Trigger: everything else (default)

Expected: ~30s for Track B vs current ~7min.

### Local Docker run — your target commands

**Option 1: Mount local code (fastest dev loop):**

```bash
docker run --rm -d --name sgp-service \
  --platform linux/amd64 \
  --add-host=host.docker.internal:host-gateway \
  -p 8000:8000 \
  -e FAST_API__AUTH__API_KEY__NAME=X-API-Key \
  -e FAST_API__AUTH__API_KEY__VALUE=local-validation-key \
  -e SG_PLAYWRIGHT__DEPLOYMENT_TARGET=laptop \
  -e SG_PLAYWRIGHT__CODE_LOCAL_PATH=/mnt/code \
  -v $(pwd):/mnt/code:ro \
  745506449035.dkr.ecr.eu-west-2.amazonaws.com/sgraph_ai_service_playwright:latest
```

Mount the repo root at `/mnt/code` so `import sgraph_ai_service_playwright` resolves.
Edit code → `docker restart sgp-service` → test. ~2 seconds per cycle.

**Option 2: Pull code from S3 (test what Lambda would see):**

```bash
docker run --rm -d --name sgp-service \
  --platform linux/amd64 \
  -p 8000:8000 \
  -e AWS_REGION=eu-west-2 \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... \
  -e SG_PLAYWRIGHT__LAMBDA_NAME=sg-playwright-dev \
  -e SG_PLAYWRIGHT__CODE_S3_VERSION=latest \
  -e FAST_API__AUTH__API_KEY__NAME=X-API-Key \
  -e FAST_API__AUTH__API_KEY__VALUE=local-validation-key \
  745506449035.dkr.ecr.eu-west-2.amazonaws.com/sgraph_ai_service_playwright:latest
```

Exact same image as Lambda, same code load path, just running your laptop. Perfect reproduction of Lambda behaviour for debugging issues like Bug #1.

**Option 3: No code loading, use whatever's baked in:**

```bash
docker run --rm -d -p 8000:8000 [...] \
  745506449035.dkr.ecr.eu-west-2.amazonaws.com/sgraph_ai_service_playwright:latest
# No AWS_REGION, no CODE_LOCAL_PATH → falls through to whatever's on sys.path
```

Useful for testing the image itself (does Playwright/Chromium still work?) without involving any code deploy.

---

## Versioning & tags — your question 3

Two axes, both visible in `/health/info`:

```json
{
  "service_name":         "sg-playwright",
  "service_version":      "v0.1.28",        // code version (from S3 zip)
  "image_version":        "runtime-v3",     // image version (ECR tag)
  "code_source":          "s3://745506449035--sg-playwright--eu-west-2/sg-playwright-dev/code/v0.1.28.zip",
  ...
}
```

**Lambda tags reflect both:**
- `code_version`: `v0.1.28`
- `image_version`: `runtime-v3`

Updated together only when you bump the runtime image. Code version updates every deploy.

Changes needed to the existing `consts/version.py`: none — it already reads a `version` file. We just need a matching `image_version` file that the Dockerfile updates when built.

---

## The error-reporting UX on failures

Given Dinis's pattern, here's what a broken deploy looks like end-to-end:

1. CI pushes `code/vBAD.zip` to S3 — zip is malformed or missing a module
2. Lambda recycles, next cold start runs `lambda_entry.py`
3. `load_code_from_s3()` succeeds (zip downloads and extracts fine)
4. `Fast_API__Playwright__Service()` raises `ImportError` or similar
5. `error` gets pinned to `"CRITICAL ERROR: Failed to start service with:\nImportError: ..."` + code_source
6. `run(event, context)` returns the error string for every request
7. Client sees the error in the response body, not a Lambda crash
8. Operator fixes: `aws s3 cp code/v0.1.27.zip code/latest.zip` (or update the env var) → next cold start loads the good version

Rollback time: ~10 seconds (S3 copy + Lambda config update). No image rebuild needed.

---

## Migration order

1. **Ship `lambda_entry.py` + new Dockerfile** as a new image tag. Lambda doesn't use it yet.
2. **Ship `package_code.py`** — manually deploy one version to S3.
3. **Cut dev Lambda** to the new image + env vars (`LAMBDA_NAME`, `CODE_S3_VERSION=vX.Y.Z`). Lambda recycles, pulls code from S3.
4. **Validate dev works.** QA reruns baseline 9/9 suite + proxy harness.
5. **CI split into Track A / Track B.**
6. **Document** the local docker commands in the briefing for future sessions.

Each step is reversible. If the S3 path misbehaves, set `CODE_S3_VERSION` back to a known-good version. If the whole S3 path is broken, flip the Lambda image back to a pre-refactor tag.

---

## Open questions — round 2

1. **`clear_osbot_aws_modules()` — do we need it here?** In your existing pattern, it's there because `load_dependencies` imports a *different* `osbot_aws` version (the boto3-only slim one baked into the image) than the full one that gets loaded via the S3 zip. In the Playwright service's case, we're not loading dependencies from S3 — only user code. So the purge may be unnecessary. Your call — keeping it costs nothing and matches your pattern.

2. **Path of `lambda_entry.py` inside the image.** I put it at the top level. Should it live in a `bootloader/` folder to match the spec's directory convention in `base-image-research.md`? Cosmetic either way.

3. **Should `lambda_entry.py` itself be part of the zip, or baked into the image?** My read: baked into the image. It's a stable shim that changes rarely; the zip contains the app, not the boot shim. Putting it in the zip creates a chicken-and-egg for the boot loader.

4. **Cold-start cache** — skip download if `/tmp/.../<version>/` already exists? Ship without this initially, add later if cold start becomes a pain point. The per-Lambda `/tmp` persists across warm invocations so this would help.

---

## Why this version is much simpler

- **No fallback service.** Your top-level try/catch pattern replaces a whole parallel FastAPI app.
- **No custom `CODE_SOURCE` enum.** Precedence order (local path > AWS_REGION+S3 > nothing) is simpler.
- **No new packaging — existing osbot primitives do the work.** `S3__Zip_Bytes.save_to_s3()` is the one-liner.
- **Matches existing `sgraph_ai_app_send` pattern** — any dev who's read that will instantly recognise the shape.

Implementation surface: ~80 lines in `lambda_entry.py`, ~30 lines in `package_code.py`, Dockerfile tweaks, CI yaml split. Total: one afternoon of work.
