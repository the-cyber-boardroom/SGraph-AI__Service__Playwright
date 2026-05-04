# Note — Docker artefact upload cost on CI

**Status:** captured for later, not an active blocker.
**Observed on:** `deploy-dev / Build Docker Image`, 2026-04-17, after the `42ecdfd` build fix went green.
**Workflow:** `.github/workflows/ci-pipeline.yml` — `build-docker-image` job.

═══════════════════════════════════════════════════════════════════════════════

## Timings as observed

| Step                             | Duration |
|----------------------------------|----------|
| Build Docker image via pytest    | 49s      |
| Save Docker image to tarball     | 13s      |
| Upload Docker image artefact     | 1m 15s   |
| **Total build-docker-image job** | **2m 38s** |

So the build itself (49s) is not the bottleneck — the post-build hops
cost roughly **88s out of 158s (~55%)**.

═══════════════════════════════════════════════════════════════════════════════

## What those steps are actually doing

1. **`Save Docker image to tarball`**
   - `docker save <ECR URI> -o image.tar` on the runner.
   - Serialises every layer (Playwright base + Python deps + Chromium) into
     one file on the runner's local disk.
   - ~1.3 GB at a guess. 13s of pure disk I/O — expected.

2. **`Upload Docker image artefact`**
   - `actions/upload-artifact@v4` with
     `name: docker-image, path: image.tar, retention-days: 1`.
   - **Destination: GitHub Actions artefact storage** (workflow-scoped,
     lives on GitHub's infra — NOT ECR, NOT S3, NOT our account).
   - GitHub-hosted runners upload artefacts at ~20 MB/s, so
     ~1.3 GB / 20 MB/s ≈ 65–75s, which matches the 1m 15s we saw.
   - Retention is 1 day — it's deleted automatically after the workflow
     ages out.

3. **Why the artefact hop exists at all**
   Two downstream jobs consume the same image:
   - `run-integration-tests` — `actions/download-artifact@v4` + `docker load`
   - `push-docker-image-ecr` — same pattern, then `docker push <ECR URI>`

   Without the artefact, each job would rebuild from scratch (another 49s
   each + Playwright cache miss), so the artefact is an optimisation. It's
   just an expensive one.

═══════════════════════════════════════════════════════════════════════════════

## Options to revisit (in rough order of effort)

- **Push to ECR directly from the build job, skip the artefact.**
  Downstream jobs pull from ECR (`docker pull`) instead of download-artifact
  + docker load. ECR pulls from a GH runner are typically 30–50 MB/s
  (cross-region) and benefit from layer caching. Trade-off: every build
  pushes a `:latest` to ECR even if integration tests are going to fail.
  Mitigation: push to a `:ci-<sha>` tag and only re-tag `:latest` after
  integration tests pass.

- **Shrink the image.**
  Playwright `v1.58.0-noble` base ships with all three browsers. We only
  use Chromium. A custom base image or `--with-deps chromium` install
  would cut hundreds of MB. Probably the highest-leverage change.

- **`docker buildx` with registry cache.**
  `cache-from`/`cache-to` against ECR or GHCR would make subsequent
  builds 5–15s instead of 49s and avoid re-uploading unchanged layers.

- **Move to self-hosted runners.**
  Artefact upload + ECR push both stay on-LAN; typical 10× speedup.
  Operational cost to run.

═══════════════════════════════════════════════════════════════════════════════

## Why we're not fixing this right now

Phase 2.10 still has Slice B (Routes__Browser) and Slice C
(Routes__Sequence) to land, plus the full 16-endpoint fan-out and the
10 deferred step actions. The 1m 15s is annoying but it's fixed cost per
build, not a correctness issue. Revisit after Phase 2.10 ships — probably
worth a dedicated "CI speed" pass that also looks at the integration-test
job's own download-artifact round trip.
