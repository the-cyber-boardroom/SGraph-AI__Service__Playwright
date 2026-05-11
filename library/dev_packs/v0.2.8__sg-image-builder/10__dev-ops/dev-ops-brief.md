# DevOps Brief — CI/CD for SG-Compute__Image-Builder

**Audience:** DevOps agent (and any developer touching the CI pipeline)
**Status:** Required from day 1; not a follow-up
**Repo:** `https://github.com/SG-Compute/SG-Compute__Image-Builder`

This brief covers the CI/CD pipeline, branch strategy, auto-tagging, the four test gates, the zipapp build target, and the secrets the repo needs to function. The pipeline must exist before the first feature PR is merged.

The principles being honoured: **P3** (every operation fully instrumented — including the CI itself), **P16** (tests are the contract), **P19** (offline-first — CI runs must work without external services where possible), **P20** (sgi ships as a zipapp — that's a build target, not a wish).

---

## Branch model

Trunk-based. Two protected branches:

- **`main`** — what release tags get cut from. Protected: no direct pushes, requires PR + green CI.
- **`dev`** — integration branch where feature PRs land first. Protected: requires green CI on the PR.

Feature work happens on short-lived branches off `dev`. PRs merge into `dev`; periodically (when `dev` is green and a coherent slice of work is done) a PR from `dev` → `main` cuts the next release.

Hotfix workflow: branch from `main`, PR back into both `main` and `dev`.

No long-lived feature branches. If a feature is too big for a single PR, break it into smaller PRs guarded by feature flags.

---

## Workflows

Three GitHub Actions workflows, one per trigger:

### 1. `.github/workflows/pr.yml` — runs on every PR

Triggers: `pull_request` to `dev` or `main`.

```yaml
jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff mypy
      - run: ruff check sg_image_builder/ sg_image_builder__tests/
      - run: ruff format --check sg_image_builder/ sg_image_builder__tests/
      - run: mypy sg_image_builder/

  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e .[test]
      - run: pytest sg_image_builder__tests/unit/ -v --cov=sg_image_builder --cov-report=xml --cov-fail-under=90
      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'

  integration-tests:
    runs-on: ubuntu-latest
    services:
      sshd:
        image: linuxserver/openssh-server
        ports:
          - 2222:2222
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .[test]
      - name: Set up localhost SSH for Exec_Provider__SSH tests
        run: |
          ssh-keygen -t ed25519 -N "" -f /tmp/sgi_ci_key
          # configure the sshd service to accept the public key
      - run: pytest sg_image_builder__tests/integration/ -v
        env:
          SGI_INTEGRATION_SSH_HOST: localhost
          SGI_INTEGRATION_SSH_PORT: 2222
          SGI_INTEGRATION_SSH_KEY: /tmp/sgi_ci_key
```

Required to pass: all three jobs. Cannot merge a PR until they're green.

### 2. `.github/workflows/main.yml` — runs on merges to `main` and `dev`

Triggers: `push` to `main` or `dev`.

Runs everything `pr.yml` runs, plus:

```yaml
  build-zipapp:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: python scripts/build_zipapp.py
      - name: Smoke-test the zipapp
        run: python dist/sgi.zipapp --version
      - uses: actions/upload-artifact@v4
        with:
          name: sgi-zipapp-${{ github.sha }}
          path: dist/sgi.zipapp
          retention-days: 30

  auto-tag:
    if: github.ref == 'refs/heads/main'
    needs: [build-zipapp]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: Read version file
        id: version
        run: echo "version=$(cat sg_image_builder/version)" >> $GITHUB_OUTPUT
      - name: Create tag if not exists
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
            git tag "$VERSION"
            git push origin "$VERSION"
          fi
```

### 3. `.github/workflows/tag.yml` — runs when a tag is pushed

Triggers: `push` of tags matching `v*`.

```yaml
jobs:
  e2e-and-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -e .[test]

      - name: Build zipapp
        run: python scripts/build_zipapp.py

      - name: Run E2E suite
        run: pytest sg_image_builder__tests/end_to_end/ -v
        env:
          SGI_E2E_ENABLED: '1'
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_E2E_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_E2E_SECRET_ACCESS_KEY }}
          AWS_REGION: eu-west-2

      - name: Create GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/sgi.zipapp
          generate_release_notes: true
```

---

## Auto-tagging

A single file at `sg_image_builder/version` holds the current version (plain text, e.g. `v0.1.0`). The `auto-tag` job in `main.yml` reads this file and creates a matching git tag IF the tag doesn't already exist.

**Convention:** developers bump the version file in the same PR that introduces a release-worthy change. The PR description states the rationale (patch / minor / major). Code review enforces semver discipline.

This means:
- Merge to `main` triggers tag creation
- Tag creation triggers E2E + release artefact
- Tags are immutable; once cut, never re-cut

If a tag needs to be re-cut (rare; usually means the release was broken), the workflow is:
1. Bump the version in `sg_image_builder/version` to the next patch
2. Open a PR with the fix
3. Merge → new tag → new release

The previous broken tag stays in history with a release note explaining it.

---

## The four test gates

| Gate | What | Runs on | Required to pass |
|---|---|---|---|
| **Lint + typecheck** | `ruff`, `mypy` | Every PR, every push | Every PR, every push |
| **Unit** | `sg_image_builder__tests/unit/`, in-memory providers | Every PR, every push | Every PR, every push |
| **Integration** | `sg_image_builder__tests/integration/`, localhost SSH + tempdir storage | Every PR, every push | Every PR, every push |
| **End-to-end** | `sg_image_builder__tests/end_to_end/` + per-spec E2E, real AWS | Tag pushes only | Tag → release pipeline |

Gating logic:

- **PRs can merge** with lint + unit + integration green
- **Releases happen** only when E2E is also green
- **E2E never runs on PRs** to keep PR turnaround fast and AWS costs bounded
- **E2E runs nightly** on `main` to catch drift (separate workflow, scheduled trigger)

### E2E test gating env vars

```
SGI_E2E_ENABLED=1                 — main switch
SGI_S3_TESTS_ENABLED=1            — storage layer S3 round-trips
SGI_GPU_TESTS_ENABLED=1           — vllm_disk / vllm_docker (expensive)
SGI_LONG_TESTS_ENABLED=1          — anything taking > 5 min
```

A test marked `@pytest.mark.gpu` skips unless `SGI_GPU_TESTS_ENABLED=1`. CI sets all four for tag-triggered runs and only the first three for nightly runs.

---

## Coverage gates

| Scope | Target | Enforced where |
|---|---|---|
| `sg_image_builder/` core | 90% | `pytest --cov-fail-under=90` in unit-tests job |
| `sg_image_builder/providers/` | 95% | Same job, separate report |
| `sg_image_builder_specs/<spec>/` | (no enforced target — E2E is the contract) | Manual review |

Coverage drops below the threshold = build red. To bump the threshold, open a PR with the new value and rationale.

---

## Zipapp build target

`scripts/build_zipapp.py` produces `dist/sgi.zipapp`:

```python
# scripts/build_zipapp.py
import zipapp
from pathlib import Path
import shutil

def build():
    src = Path('sg_image_builder')
    staging = Path('dist/staging')
    staging.mkdir(parents=True, exist_ok=True)

    # copy package
    shutil.copytree(src, staging / 'sg_image_builder', dirs_exist_ok=True)

    # copy bundled deps (vendored at build time for offline use)
    # ...

    zipapp.create_archive(
        source=staging,
        target='dist/sgi.zipapp',
        interpreter='/usr/bin/env python3',
        main='sg_image_builder.cli.app:app',
    )

    Path('dist/sgi.zipapp').chmod(0o755)

if __name__ == '__main__':
    build()
```

The zipapp must:

- Run as `./sgi.zipapp <command>` on any Linux host with Python 3.11+
- Be self-contained: no `pip install` needed
- Pass `sgi --version` and `sgi doctor` after extraction
- Be smoke-tested in the CI job before being attached to a release

For P20 (offline-first distribution), the zipapp vendors its non-stdlib dependencies. The build script handles this — implementation detail.

---

## Required secrets

Set at the GitHub repo level (Settings → Secrets and variables → Actions):

| Secret | Purpose | Required for |
|---|---|---|
| `AWS_E2E_ACCESS_KEY_ID` | Dedicated IAM user for E2E tests | tag.yml + nightly.yml |
| `AWS_E2E_SECRET_ACCESS_KEY` | Same | tag.yml + nightly.yml |
| `CODECOV_TOKEN` | Coverage reporting | pr.yml (optional) |
| `ELASTIC_URL` (optional) | Ship events from CI runs to Kibana | All workflows (optional) |
| `ELASTIC_API_KEY` (optional) | Same | All workflows (optional) |

The E2E IAM user should have a narrowly-scoped policy:
- `ec2:RunInstances` with resource constraints (tag-based)
- `ec2:DescribeInstances`, `ec2:TerminateInstances`
- `ec2:CreateKeyPair`, `ec2:DeleteKeyPair`, `ec2:DescribeKeyPairs`
- `ec2:AuthorizeSecurityGroupIngress`, `ec2:RevokeSecurityGroupIngress`
- `s3:*` on a specific bucket: `sg-compute-sgi-ci-artifacts-*`
- `ssm:StartSession`, `ssm:SendCommand` (only if we keep Sg_Compute provider tests)

The IAM user is **never** used for anything except CI. Real engineering work uses developer credentials.

---

## Branch protection rules

For `main`:
- Require PR before merge
- Require 1 approving review
- Require status checks: `lint-and-typecheck`, `unit-tests (3.11)`, `integration-tests`, `build-zipapp`
- Require branches to be up to date before merging
- Dismiss stale reviews on new commits
- Restrict pushes that create matching branches

For `dev`:
- Same, but without the approving review requirement (allow self-merge for fast iteration)

---

## Performance budget for CI

CI cost matters. Targets:

| Workflow | Target wall-clock | Notes |
|---|---|---|
| `pr.yml` | < 5 minutes | Unit + integration only; fast feedback for developers |
| `main.yml` | < 8 minutes | Adds zipapp build |
| `tag.yml` | < 30 minutes | Includes full E2E; this is the slow one |
| Nightly | < 45 minutes | E2E + extended specs |

If CI exceeds these targets consistently, file an issue. Investigation is part of the DevOps role.

Cost ceiling for E2E: **$10/day** average across all workflows. If we're exceeding, gate more aggressively.

---

## Local dev: matching CI

A `Makefile` (or equivalent) provides one-liners:

```makefile
.PHONY: lint test unit integration e2e zipapp

lint:
	ruff check sg_image_builder/ sg_image_builder__tests/
	mypy sg_image_builder/

test: unit integration

unit:
	pytest sg_image_builder__tests/unit/ -v

integration:
	pytest sg_image_builder__tests/integration/ -v

e2e:
	SGI_E2E_ENABLED=1 pytest sg_image_builder__tests/end_to_end/ -v

zipapp:
	python scripts/build_zipapp.py
```

Developers run `make test` before pushing. The pre-push hook (optional, in `.git/hooks/pre-push`) runs `make lint test` automatically.

---

## Observability for CI itself

CI runs themselves emit events to the same event bus (P3). The `tag.yml` workflow ships its run record (timing, outcome, artefacts produced) to the configured Elasticsearch instance via the same `Events__Sink__Elasticsearch` that sgi proper uses.

This means: the Kibana dashboards visualise CI health alongside spec benchmarks. The release cadence, success rate, and time-to-merge become first-class metrics.

---

## What this brief explicitly does NOT cover

- Deployment of the zipapp itself (it's a download, not a deploy)
- Multi-region E2E (v2)
- Performance regression detection (v2)
- Automated dependency updates (Dependabot config — v0.2)
- Security scanning of dependencies (v0.2)
- Container image builds (sgi doesn't have one; the zipapp is the distribution)

These are real concerns, just not v0.1.0.

---

## First steps for the DevOps agent

1. Read this brief in full
2. Read [01__principles/principles.md](../01__principles/principles.md) for context
3. Read [09__implementation-plan/implementation-plan.md](../09__implementation-plan/implementation-plan.md) milestone M0
4. Set up the three workflow files
5. Configure branch protection
6. Generate and document the AWS IAM policy for the E2E user
7. Get the first PR (the repo skeleton) merged with green CI
8. File issues for anything ambiguous in this brief — don't guess
