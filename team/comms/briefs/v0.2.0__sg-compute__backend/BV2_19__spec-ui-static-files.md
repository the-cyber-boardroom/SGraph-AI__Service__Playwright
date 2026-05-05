# BV2.19 — Spec UI static-file serving (`StaticFiles` mount in `Fast_API__Compute`)

## Goal

FV2.6 (per-spec UI co-location) moves each spec's card + detail web components from the dashboard tree into `sg_compute_specs/<spec_id>/ui/`. Once those files live inside the Python package, the control plane must serve them so the browser can load them.

This phase adds the infrastructure: one `StaticFiles` mount per registered spec, activated only when the spec's `ui/` directory exists. The dashboard's `admin/index.html` script tags then point to `/api/specs/<spec_id>/ui/...` instead of relative dashboard paths.

**Unblocks:** FV2.6 (per-spec UI co-location — the first spec migration can't land until this is live).

---

## Why `StaticFiles` (not a streaming endpoint)

The Architect decision (2026-05-05) chose `StaticFiles` over a bespoke streaming endpoint for three reasons:

1. **Zero route logic** — FastAPI/Starlette handles MIME type, `If-None-Match`, range requests.
2. **CF+S3 / `tools.sgraph.ai` parity** — the production path replaces the `StaticFiles` origin with a CloudFront distribution backed by S3 at the same URL prefix. No dashboard changes needed at that migration.
3. **IFD versioning is immutable** — paths like `/api/specs/docker/ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.js` never change once published; long `Cache-Control` is safe.

---

## Tasks

### 1 — Resolve the `ui/` path for each spec

Add a helper `ui_path_for_spec(spec_id: str) -> Path | None` in `sg_compute/core/spec/Spec__UI__Resolver.py`:

```python
import importlib, pathlib

def ui_path_for_spec(spec_id: str):
    try:
        pkg = importlib.import_module(f'sg_compute_specs.{spec_id}')
        path = pathlib.Path(pkg.__file__).parent / 'ui'
        return path if path.is_dir() else None
    except ModuleNotFoundError:
        return None
```

`Spec__UI__Resolver` must be a `Type_Safe` class wrapping this logic, not a bare function — follow the class-per-file rule.

### 2 — Mount in `Fast_API__Compute.setup_routes()`

```python
from starlette.staticfiles import StaticFiles
from sg_compute.core.spec.Spec__UI__Resolver import Spec__UI__Resolver

resolver = Spec__UI__Resolver()
for manifest in Spec__Loader().load_all():
    ui_path = resolver.ui_path_for_spec(manifest.spec_id)
    if ui_path:
        self.app.mount(
            f'/api/specs/{manifest.spec_id}/ui',
            StaticFiles(directory=str(ui_path)),
            name=f'spec-ui-{manifest.spec_id}',
        )
```

Mount **before** the per-spec API routes are registered, so Starlette's path-matching gives the static prefix priority over any `{path:path}` catchall (none exists today, but future-proof).

### 3 — Add `Cache-Control` middleware

IFD-versioned paths are immutable. Add a `Middleware` (or response hook) that sets:

```
Cache-Control: public, max-age=31536000, immutable
```

…for any response whose URL path matches `/api/specs/*/ui/*/v*/v*.*.*/*`.

Non-versioned requests (e.g. `/api/specs/docker/ui/` directory listing — which `StaticFiles` 404s by default) get no special header.

### 4 — Verify Lambda deployment includes `ui/` folders

The Lambda packaging step (in `scripts/` or CI) must include `sg_compute_specs/**` in the zip. Check that `pyproject.toml` package data globs cover `ui/**`:

```toml
[tool.setuptools.package-data]
sg_compute_specs = ["*/ui/**/*"]
```

If it's missing, add it. Without this, the Lambda filesystem won't have the `ui/` folders and `StaticFiles` will not activate.

### 5 — Test (in-memory, no mocks)

```python
# test_Spec__UI__Static__Files.py
from sg_compute.control_plane.Fast_API__Compute import Fast_API__Compute
from starlette.testclient import TestClient

def test_spec_ui_mount_activated_when_ui_folder_exists(tmp_path):
    # create a fake ui/ tree
    spec_id = 'docker'
    ui_dir   = tmp_path / 'sg_compute_specs' / spec_id / 'ui' / 'card' / 'v0' / 'v0.1' / 'v0.1.0'
    ui_dir.mkdir(parents=True)
    (ui_dir / 'sg-compute-docker-card.js').write_text('// test')

    compute = Fast_API__Compute(ui_root_override=tmp_path)
    compute.setup_routes()
    client = TestClient(compute.app)

    resp = client.get(f'/api/specs/{spec_id}/ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.js')
    assert resp.status_code == 200
    assert 'test' in resp.text

def test_spec_ui_no_mount_when_ui_folder_absent():
    compute = Fast_API__Compute()
    # no ui/ dirs exist in sg_compute_specs/ yet
    compute.setup_routes()
    client = TestClient(compute.app)
    resp = client.get('/api/specs/docker/ui/nonexistent.js')
    assert resp.status_code == 404
```

`ui_root_override` allows tests to point `Spec__UI__Resolver` at a temp directory — inject it as a `Type_Safe` attribute, not a mock.

---

## Acceptance criteria

- `GET /api/specs/docker/ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.js` returns `200` with correct `Content-Type: application/javascript` once the `docker` spec has a `ui/` folder.
- `GET /api/specs/ollama/ui/anything` returns `404` (no `ui/` folder for ollama yet — mount not activated).
- `Cache-Control: public, max-age=31536000, immutable` on versioned path responses.
- `sg_compute_specs = ["*/ui/**/*"]` in `pyproject.toml` package-data.
- `tests/ci/test_no_legacy_imports.py` still passes (no new legacy imports introduced).
- All existing tests still pass.
- Reality doc updated.

---

## Open questions

None — Architect decision 2026-05-05 settled the serving mechanism.

---

## Blocks / Blocked by

- **Blocks:** FV2.6 (per-spec UI co-location — the first spec can't be migrated until this mount exists and serves correctly).
- **Blocked by:** BV2.13 (spec layout normalisation) is recommended first, so the `ui/` folder convention is locked before the mount code is written. Can run in parallel if needed — the mount gracefully no-ops for specs with no `ui/` directory.

---

## Notes

- The `StaticFiles` mount is skipped silently when no `ui/` folder exists — this means BV2.19 can ship before any spec has a `ui/` folder without breaking anything.
- The `ui/` folder convention is: `sg_compute_specs/<spec_id>/ui/card/v{M}/v{M}.{m}/v{M}.{m}.{p}/sg-compute-<spec_id>-card.{js,html,css}` and same for `ui/detail/`.
- Production swap: when `tools.sgraph.ai` is ready, replace the `StaticFiles` mount with a redirect to `https://tools.sgraph.ai/specs/<spec_id>/ui/...`. No dashboard changes needed — the URL prefix is the same.
