# BV2.12 — Delete `agent_mitmproxy/`; shim 8 legacy `__cli/<spec>/` dirs

## Goal

Two related cleanups now that the Lambda packaging is cut over (BV2.11):

- Delete the legacy `agent_mitmproxy/` tree at the repo root. The mitmproxy spec lives at `sg_compute_specs/mitmproxy/` and is functional.
- Convert the 8 legacy `sgraph_ai_service_playwright__cli/<spec>/` directories (docker, podman, vnc, neko, prometheus, opensearch, elastic, firefox) into deprecation-warning re-export shims.

The original v0.1.140 backend plan §3.10 required these shims from the start; they were never created. This phase finally delivers them.

## Tasks

1. **Verify `sg_compute_specs/mitmproxy/`** is the canonical mitmproxy spec — `manifest.py` works, tests pass, dockerfile builds.
2. **Verify nothing outside `agent_mitmproxy/` imports it** — `grep -rln 'from agent_mitmproxy\|import agent_mitmproxy' .`. Should return zero hits or only legacy script entries that BV2.11 should have updated.
3. **Delete `agent_mitmproxy/`** at the repo root.
4. **Verify CI** — both `dev` and `main` pipelines green.
5. **For each of the 8 specs**, convert the legacy `__cli/<spec>/` directory to a re-export shim. Pattern:

   ```python
   # sgraph_ai_service_playwright__cli/docker/__init__.py
   import warnings
   warnings.warn(
       "sgraph_ai_service_playwright__cli.docker is deprecated; "
       "use sg_compute_specs.docker instead. Will be removed in v0.3.0.",
       DeprecationWarning,
       stacklevel=2,
   )
   from sg_compute_specs.docker import *  # noqa
   from sg_compute_specs.docker.manifest import MANIFEST  # noqa
   ```
   
   Sub-modules (e.g. `__cli/docker/service/Docker__Service.py`) become thin re-exports too:
   ```python
   from sg_compute_specs.docker.service.Docker__Service import Docker__Service
   ```
   
6. **Search for the `linux` legacy directory** — should be deleted (linux was dropped intentionally; legacy review confirmed). `git rm -r sgraph_ai_service_playwright__cli/linux/` if present.

7. Update reality doc.

## Acceptance criteria

- `agent_mitmproxy/` does not exist on disk.
- Each of the 8 `__cli/<spec>/` directories is reduced to shim files (not full code). `wc -l __cli/docker/service/Docker__Service.py` should be < 5 lines.
- `sgraph_ai_service_playwright__cli/linux/` does not exist.
- All tests pass; deprecation warnings show up but don't fail.
- Reality doc updated.

## Open questions

- **Shim removal deadline.** When are the shims deleted? Recommend v0.3.0 — the deprecation warning gives consumers a release window.

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** BV2.11 (Lambda cutover) — `lambda_entry.py` and the Dockerfile must already point at the new path.

## Notes

After this phase, the only legacy code remaining at the repo root is `sgraph_ai_service_playwright__cli/` itself with shimmed sub-packages plus whatever non-spec-specific code it still owns (e.g. `aws/`, `core/`, etc. that BV2.7 didn't migrate). v0.3.x finishes that migration; this phase doesn't need to.
