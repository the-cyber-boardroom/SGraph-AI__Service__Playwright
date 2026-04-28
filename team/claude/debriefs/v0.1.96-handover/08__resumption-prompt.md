# 08 — Resumption Prompt

Copy-paste this to a fresh agent session.

---

```
I'm continuing the v0.1.96 playwright stack split refactor on branch
claude/refactor-playwright-image-FVPDf.

Read the handover dev-pack at team/claude/debriefs/v0.1.96-handover/
in numerical order (00 → 08). It contains:
  - the original task and signed-off 8-doc plan
  - what's shipped (Phase A done, sp os complete, sp prom 6a done)
  - patterns + conventions established
  - lessons learned (bugs caught, invariants locked)
  - key commits to read
  - the proven sister-section template
  - remaining phases with concrete next-up

Then read CLAUDE.md (project rules) and check the current reality doc
under team/roles/librarian/reality/.

Pick up at Phase B step 6b — sp prom schemas + collections.

Constraints I must respect:
  - Small files, single responsibility (operator-mandated)
  - One class per file; never use Pydantic / dataclass / raw dicts
  - No mocks, no patches, no MagicMock — only real _Fake_* subclasses
    that override the AWS / HTTP boundary methods
  - Type_Safe everywhere; no_args_is_help; ═══ headers; inline comments
  - Update the reality doc + file a debrief in the same commit
  - Sync with origin/dev and origin/claude/observability-pipeline-architecture-8p9k1
    before each commit

Environment setup (one-time, only if pytest / packages aren't already
in a usable Python 3.12 env):

  python3.12 -m venv /tmp/venv-sp
  /tmp/venv-sp/bin/pip install -r requirements.txt -e . pytest pytest-timeout

Run tests via:
  /tmp/venv-sp/bin/python -m pytest tests/unit/ --timeout=30 \
      --ignore=tests/unit/agent_mitmproxy -q --no-header

Pre-existing flake (NOT a regression):
  test_S3__Inventory__Lister::test_empty_region_does_not_pass_region_name
  in lets/cf/inventory/service/ — network-dependent; predates this branch.

When in doubt, follow the sp os template (commit f5dcde7 for AWS
helpers; commit 2b21126 for create_stack composition). When picking
sp prom slice sizes, target ≤ 100 lines per code file and ≤ 150 lines
per test file.
```

---

## Quick-reference paths

| What | Path |
|---|---|
| The plan (8 approved docs) | `team/comms/plans/v0.1.96__playwright-stack-split__*.md` |
| Per-slice debriefs | `team/claude/debriefs/2026-04-26__playwright-stack-split__*.md` (21 of them) |
| Debriefs index | `team/claude/debriefs/index.md` |
| Reality doc — sister sections | `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` |
| Shared infra (use these) | `cli/aws/Stack__Naming.py`, `cli/image/Image__Build__Service.py`, `cli/ec2/service/Ec2__AWS__Client.py` |
| `sp os` reference (mirror this) | `cli/opensearch/` + `tests/unit/.../opensearch/` + `scripts/opensearch.py` |
| `sp prom` foundation (continue here) | `cli/prometheus/` + `tests/unit/.../prometheus/` |
| Project rules | `.claude/CLAUDE.md` |

## Branch state at handover

```
$ git log --oneline -1 claude/refactor-playwright-image-FVPDf
98d3991 docs(debriefs): backfill 7 missing Phase B sub-slice debriefs
```

(Last code commit was `1a19d3f` — `sp prom` foundation. The `98d3991` commit only adds backfilled debrief docs.)

## After this pack lands

The dev-pack itself becomes another commit. After that, the next agent's first commit is `feat(cli): Phase B step 6b — sp prom schemas + collections`.
