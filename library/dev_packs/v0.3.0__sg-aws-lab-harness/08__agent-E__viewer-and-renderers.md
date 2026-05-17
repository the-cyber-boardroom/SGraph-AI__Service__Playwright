---
title: "08 — Agent E — Viewer + diff + HTML renderers (P5)"
file: 08__agent-E__viewer-and-renderers.md
author: Architect (Claude)
date: 2026-05-17 (rev 2)
parent: README.md
size: S (small) — ~700 prod lines, ~300 test lines, ~1 day
depends_on: Foundation PR (no dependency on A/B/C/D)
mandatory_reading:
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md  # §B.1 — §B.7
delivers: lab P5 from lab-brief/07 — fully independent slice
---

# Agent E — Viewer + diff + HTML renderers

The fully-independent slice. Can land any time after the Foundation. Doesn't block — and isn't blocked by — A/B/C/D.

The deliverable is the operator-friendly read side of the harness: an HTML viewer, a runs-diff command, and the HTML renderer for results.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/`

**Files to create:**

- `service/Lab__Viewer__App.py` — FastAPI app reading `.sg-lab/runs/`
- `service/Lab__Runs__Diff.py` — schema-walking diff with sign/Δ rendering
- `service/renderers/Render__HTML.py` — every Schema__Lab__Result__* renderable as HTML (cards, tables, simple SVG for timelines/histograms)
- `service/renderers/Render__Diff__Terminal.py` — colourised side-by-side terminal diff for `runs diff`
- CLI surface fill-in: implement `Cli__Lab.py serve` (foundation shipped stub) and `Cli__Lab.py runs diff` (foundation shipped stub)
- Templates under `service/viewer_templates/` — Jinja2 templates for the index page, run-detail page, diff page

**Plus:**

- A copy of the architecture diagrams referenced in `lab-brief/06 §2` (ASCII + SVG) — these go on the viewer index page so an operator opening the viewer sees the harness's mental model alongside the runs list.

---

## What you do NOT touch

- Any experiment file (no `experiments/*/E*` modifications)
- Any `Lab__Teardown__*.py`
- Any other agent's renderers (`Render__Timeline__ASCII` — Agent A and D; `Render__Histogram__ASCII` — Agent B; `Render__Table` and `Render__JSON` — Foundation)
- `aws/cf/`, `aws/lambda_/` packages
- The registry (no new experiments)

---

## Why this is independent

The viewer reads from `.sg-lab/runs/<run-id>/result.json`. The result JSON files are produced by Foundation's `Lab__Runner` and shaped by `Schema__Lab__Run__Result` (also Foundation).

You don't care which agent produced a particular `result.json` — your viewer reads them all. You can develop and test against synthetic `result.json` files you write yourself.

This means **Agent E can ship before any of A/B/C/D have written a single experiment.** Empty `.sg-lab/runs/` should render as "no runs yet" — write tests for that.

---

## Surface

### `sg aws lab serve [--port 8090] [--host 127.0.0.1]`

Starts the FastAPI app. Routes:

| Route | Renders |
|-------|---------|
| `/` | Index page — architecture diagrams + list of runs newest-first, grouped by experiment |
| `/runs/<run-id>` | One run's result rendered as cards (one card per top-level result field) + the ledger if requested + the timeline / histogram inline as SVG |
| `/runs/<run-id-A>/diff/<run-id-B>` | Side-by-side diff of two runs of the same experiment |
| `/schemas/<experiment-id>` | The result schema as a JSON-Schema-style doc — useful when integrating viewer output with other tools |
| `/health` | `{"status": "ok", "runs_count": N}` |

Bind to `127.0.0.1` by default — **never** expose by default. `--host 0.0.0.0` requires explicit pass.

### `sg aws lab runs diff <run-id-A> <run-id-B>`

Terminal side-by-side diff:

- Schema-walks both `Schema__Lab__Run__Result`s.
- Aligns matching fields.
- For numeric fields renders the delta with sign and percentage.
- Highlights regressions (a `duration_ms` that grew) in red, improvements in green.

Refuses (with a clear error) if the two runs are of different experiments.

---

## Reuse, don't rewrite

| Existing class / library | Use for |
|--------------------------|---------|
| `osbot-fast-api-serverless` Fast_API base | Foundation of the viewer app |
| Jinja2 (via FastAPI) | Templates |
| `Schema__Lab__Run__Result` (Foundation) | The shape you walk |
| Existing `library/guides/v0.24.2__fast_api_routes.md` | Route class style |
| Existing `Render__Table` (Foundation) | If you want HTML tables, you can adapt the renderer pattern |

---

## Risks to watch

- **Don't bind to 0.0.0.0 by default.** A misconfigured `serve` exposing `.sg-lab/` over the network leaks AWS account IDs, ARNs, IP addresses, and timing data. Default `127.0.0.1`, refuse `0.0.0.0` without an explicit flag, refuse a non-localhost flag without a printed warning.
- **HTML XSS.** Result schemas have string fields that come from AWS responses or experiment-author code. Treat every string as untrusted — Jinja2's autoescape is on by default; keep it on.
- **Diff schema mismatch.** Two runs of the same experiment may have *slightly* different schema shapes if the experiment schema evolved between them. Detect and warn — don't crash.
- **Viewer must not load in compute-busy mode.** Reading hundreds of result.json files at app boot is fine; reading them all on every page render is not. Use a 1-min in-memory cache of `(run-id, result)` tuples.
- **Templates checked into git.** Templates live under `service/viewer_templates/*.html` — these are tracked, not generated. Don't write a template-generator.

---

## Acceptance

```bash
# create a few synthetic runs to test against
mkdir -p .sg-lab/runs/2026-05-17T10-00-00Z__abc123
echo '{...synthetic result...}' > .sg-lab/runs/2026-05-17T10-00-00Z__abc123/result.json

# 1. serve
sg aws lab serve --port 8090 &
curl -s http://127.0.0.1:8090/health
# → {"status":"ok","runs_count":1}

curl -s http://127.0.0.1:8090/runs/2026-05-17T10-00-00Z__abc123 | grep "experiment"
# → renders run

# 2. diff
sg aws lab runs diff 2026-05-17T10-00-00Z__abc123 2026-05-17T10-15-00Z__def456
# → terminal diff with deltas

# 3. refuse 0.0.0.0 without explicit flag
sg aws lab serve --host 0.0.0.0
# → error: binding to non-localhost requires --i-know-this-is-public
```

Plus:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/ -k "viewer or diff or html" -v
```

---

## What "done" looks like

- An operator can `sg aws lab serve` and browse the harness output without leaving the terminal-as-UI feel.
- Side-by-side diff of two runs of E11 makes a regression visible in <2 seconds.
- The viewer index page educates a new operator about the harness shape (architecture diagram is right there).
- Default bind is `127.0.0.1`.

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-viewer`. Commit prefix: `feat(v0.3.0): lab agent-E — viewer + diff + HTML renderers`.

Open PR against `claude/aws-primitives-support-NVyEh`.
