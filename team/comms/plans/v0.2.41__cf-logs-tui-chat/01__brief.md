---
title: "Design Brief — sg el lets cf tui chat: talk to the CloudFront/CloudWatch log data (and the TUI)"
file: 01__brief.md
author: Dev (Claude)
date: 2026-05-22
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (merged dev v0.2.39 line)
status: PLAN — no code, no commits. For human ratification before any build.
parent:
  - team/humans/dinis_cruz/claude-code-web/05/21/14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md
  - team/claude/debriefs/2026-05-21__v0.2.36-bedrock-chat-tui.md
  - team/claude/debriefs/2026-05-21__v0.2.40-sg-aws-auth-and-lets-cf-iam.md
---

# Design Brief — `sg el lets cf tui chat`

> **PROPOSED — does not exist yet.** This is a reuse plan. The Bedrock chat engine,
> the chat widgets, the CF-logs data sources, and the shared `cli/tui/` framework all
> exist on `dev`; this brief proposes wiring them together. No code has been written.

---

## 1. The idea, in one line

Add a chat panel to the CloudFront-logs ("CloudWatch") TUI so an operator can **ask
questions of the live log data** — *"why did 4xx spike at 14:30?"*, *"which country
drove the bot traffic?"*, *"is the Firehose→S3 hop healthy?"* — answered by the existing
Bedrock chat engine, grounded in the snapshots the CF TUI already produces, and
(Layer 2) able to **drive the TUI** (sync this hour, wipe an index, drill to a record).

## 2. Why this is powerful (and cheap)

Three already-built systems were designed to meet here:

- **The chat engine is provider-agnostic and context-seeded.** `Bedrock__Chat__Engine`
  takes an injected source and a `Schema__Bedrock__Chat__Context(label, body)` whose own
  header literally reads *"The 'talk to the data' seam … an sg edge snapshot rendered to
  markdown."* Feeding log data in is **one object**, no new plumbing.
- **The CF TUI already renders the exact data.** `CF_TUI__Data_Source.traffic_snapshot()`
  → `Schema__CF_TUI__Traffic_Snapshot` (top URIs, status classes, top countries, top
  bots, per-minute throughput, bot/human/cache counts); `CF_TUI__Card().render(snapshot)`
  already turns it into a text card. `read_record()` gives full 38-field lineage for one
  line; `CF_TUI__Arch_Source.snapshot()` gives the live CF→Firehose→S3→CloudWatch wiring.
- **It rides on the v0.2.40 auth work.** The Bedrock client and the CF clients both go
  through `Sg__Aws__Session.from_context()` — the chokepoint P1 converged onto. So
  transparent assume + the auth-error guard already cover a chat command; we only add a
  `bedrock:InvokeModel` grant to a role profile (see §7).

The brief `…/v0.2.36__tui-api-standard/` frames the end-state: every TUI exposes a
`Tui_Api__Provider` (`manifest/state/actions/dispatch/export/orientation`), and the chat
is both a **consumer** (drives other tools) and a producer. This brief is the CF-logs
instantiation of that standard.

---

## 3. What exists today (reuse inventory, code-verified)

| Asset | Path | Reuse |
|-------|------|-------|
| Chat engine (provider-agnostic) | `aws/bedrock/tui/service/Bedrock__Chat__Engine.py` | **as-is** — `new_session(region, model_alias, context, budget_usd)`, `send_turn(session, user_text, on_delta=…)` |
| Context seam | `aws/bedrock/tui/schemas/Schema__Bedrock__Chat__Context.py` | **as-is** — `(label, body)` → system prompt |
| Session/message/turn schemas | `aws/bedrock/tui/schemas/Schema__Bedrock__Chat__{Session,Message,Turn}.py` | **as-is** |
| Source seam | `aws/bedrock/tui/source/Bedrock__Chat__Source.py` (+ `…AWS_Source`, `…In_Memory`) | **as-is** — `stream_turn` / `converse_turn` |
| Chat widgets | `aws/bedrock/tui/screens/widgets/Chat__{Bubble,Composer,Cost__Meter}.py` | **reuse**, ideally promote (§6) |
| Bedrock client boundary | `aws/bedrock/service/Bedrock__Runtime__AWS__Client.py` | **as-is** — `client()` via `Sg__Aws__Session` |
| Shared TUI base | `cli/tui/components/Tui__App.py` | **subclass** — `populate()`, `log_event()`, Debug Panel free |
| Debug feed | `cli/tui/debug/Debug__Event_Log.py` + `components/Debug__Panel.py` | **reuse** — log model round-trips + S3 reads |
| CF data sources | `elastic/lets/cf/tui/source/CF_TUI__{Data_Source,S3_Source,In_Memory_Source,Arch_Source}.py` | **consume** for context |
| Snapshot → text | `elastic/lets/cf/tui/service/CF_TUI__Card.py` (`render(snapshot)`) | **reuse** to build `context.body` |

Nothing here needs rewriting. The work is composition + a thin "context builder" + (Layer 2) a provider.

---

## 4. Design — Layer 1: talk to the data

New command `sg el lets cf tui chat` (in `tui/cli/Cli__CF__Tui.py`), guarded by the
existing `@aws_auth_guard('el-lets-cf')` so transparent assume + the auth menu apply.

Flow:
1. Build the CF data source (same `_source()`/`_arch_source()` factories the other
   screens use; `--source s3|in-memory`, `--date/--hour` scope).
2. **Context builder** (new, pure): assemble `Schema__Bedrock__Chat__Context` whose
   `body` is the rendered traffic card + a compact architecture summary + scope
   metadata. `label` = e.g. `"CF logs s3 2026-05-21 14:00 (320 events, 12 files)"`.
3. `engine = Bedrock__Chat__Engine(source=Bedrock__Chat__AWS_Source())`;
   `session = engine.new_session(context=ctx, model_alias=…, budget_usd=…)`.
4. TTY → a Textual chat screen (reuse the chat widgets); non-TTY → one-shot
   (read stdin prompt → `send_turn` → print answer + cost), matching the bedrock
   chat-tui's pipe-safe pattern.
5. Debug Panel shows the under-the-hood feed (s3.list/s3.get + `bedrock.invoke`
   + token/$), via the shared `Debug__Event_Log`.

The only genuinely new code is the **context builder** and the **screen wiring**.

### New schema (Layer 1)

- `Schema__CF_Chat__Context__Spec` (optional) — what to include: `traffic` (bool),
  `architecture` (bool), `record_key`/`line` (drill a specific record into context),
  `max_chars` (truncate to keep cost bounded). Keeps context assembly declarative and
  testable.

### Files (Layer 1)

```
elastic/lets/cf/tui/chat/
  CF_Chat__Context__Builder.py        # CF snapshot(s) → Schema__Bedrock__Chat__Context (pure, tested)
  schemas/Schema__CF_Chat__Context__Spec.py
  cli/  (or extend tui/cli/Cli__CF__Tui.py with the `chat` command)
  tests/test_CF_Chat__Context__Builder.py
  tests/test_Cli__CF__Chat.py         # one-shot path with an in-memory chat source + in-memory CF source
```
Plus the screen: reuse `Bedrock__Chat__Screen` if it is generic enough, else a thin
`CF_TUI__Screen__Chat(Tui__App)` composing the chat widgets.

---

## 5. Design — Layer 2: talk to the TUI (the standard)

Give the CF-logs TUI a `Tui_Api__Provider` (per the TUI-API brief) so the chat can do
more than read a frozen snapshot — it can **query live** and **act**:

- `state()` → current scope + the latest snapshot as structured JSON.
- `actions_available(grants)` → `sync(date,hour)`, `wipe`, `consolidate`,
  `read_record(key,line)`, `list_files(date,hour)` — filtered by the scopes the active
  role grants (ties into `sg-lets-cf`).
- `dispatch(action, params)` → executes via the **existing native command bodies**
  (no new logic; the TUI-is-a-GUI-over-the-CLI rule holds), each mutation still behind
  `SG_AWS__IAM__ALLOW_MUTATIONS` / confirm.
- `export(view, fmt)` / `orientation()` → "now what?" suggestions the chat can surface.

The chat engine already has an **agentic path** (`send_turn_agentic(..., registry,
center, tool_config, grants, …)`); Layer 2 is largely "expose CF actions as tools in
that registry." This is the higher-effort, higher-power half and should follow Layer 1.

---

## 6. Reuse vs promote (avoid coupling to `aws/bedrock/`)

The chat engine, source seam, session schemas, and the three widgets are
provider-agnostic but currently live under `aws/bedrock/tui/`. Importing them from
`elastic/lets/cf/` is allowed but creates a cross-domain dependency. Recommended:
**promote the provider-agnostic chat core to `cli/tui/chat/`** (engine, source seam,
session/message/turn schemas, the 3 widgets), leaving the Bedrock-specific source
(`…AWS_Source`) and the Nova model/pricing in `aws/bedrock/`. Then both the bedrock
chat-tui and the CF chat import from the shared home. (This is the "Layer 1 + promote
widgets" option; it is a refactor of imports + file moves, no behaviour change, and
should be its own commit with the bedrock tests still green.)

Decision needed: promote now (clean, slightly more churn) vs import-from-bedrock now and
promote later (faster first slice). Default recommendation: **promote**, because the
sg-edge TUI will want the same chat and three consumers justify the shared home.

---

## 7. Auth / cost tie-in (v0.2.40)

- Add `bedrock:InvokeModel` (+ `bedrock:InvokeModelWithResponseStream`) to a role
  profile. Two options: extend the `el-lets-cf` profile, or register a dedicated
  `bedrock-chat` family. Recommendation: a small **separate `bedrock` grant** added to
  the `el-lets-cf` profile's statements (one statement, region-scoped to the Nova model
  ARNs) so `sg el lets cf iam create` provisions chat access alongside log access.
- Cost is already first-class in the engine (per-turn + per-session token/USD, budget
  bar, per-call cap confirm) — surface it in the Debug Panel and the screen footer.

---

## 8. Testing (no mocks, per house rules)

- **Context builder** — pure: feed a fixture `Schema__CF_TUI__Traffic_Snapshot` →
  assert the `Schema__Bedrock__Chat__Context.body` contains the expected tallies and is
  truncated to `max_chars`.
- **One-shot CLI** — inject `Bedrock__Chat__In_Memory` (scripted reply) + the CF
  `In_Memory_Source`; assert the answer + cost render and no AWS is touched.
- **Screen** — `App.run_test()` with the in-memory chat source (the bedrock chat-tui
  test pattern), gated on Textual/py3.12 like the other TUI tests.
- Reuse the in-memory sources verbatim → zero AWS in CI.

---

## 9. Risks / open questions

1. **Is `Bedrock__Chat__Screen` reusable as-is, or do we need a CF-specific screen?**
   Needs a read of the screen to confirm how tightly it binds to the bedrock model
   picker. (Layer-1 unknown to resolve first.)
2. **Context size vs cost.** Snapshots are small, but `read_record` + raw lines can grow;
   `max_chars` + a "what to include" spec keep token spend bounded and predictable.
3. **Promote-now vs later** (§6) — the one structural decision before coding.
4. **Layer 2 scope** — exposing mutating actions to an LLM is powerful and risky; keep it
   behind the mutation gate + confirm, and start with read-only actions
   (`read_record`, `list_files`, `state`) before `sync`/`wipe`.

## 10. Non-goals (for the first slices)

- No new model provider; Nova via the existing Bedrock source.
- No web API / web UI (that's later in the `capability → CLI → TUI → Web` sequence).
- No persistence of chat sessions (ephemeral, discarded on close — as the bedrock TUI).

---

## 11. Suggested sequencing

1. **S1 — promote chat core to `cli/tui/chat/`** (imports + moves; bedrock tests green).
2. **S2 — CF context builder + `sg el lets cf tui chat`** (Layer 1: talk to the data),
   one-shot + screen, in-memory tests.
3. **S3 — `bedrock` grant in the role profile** + `iam` re-apply path.
4. **S4 — `Tui_Api__Provider` for the CF TUI**, read-only actions first (Layer 2).
5. **S5 — mutating actions** (`sync`/`consolidate`/`wipe`) behind the gate, via the
   agentic tool registry.

Each slice is independently shippable and testable; S1–S2 deliver the headline
"talk to your CloudWatch data" experience.
