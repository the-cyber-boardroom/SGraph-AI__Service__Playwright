---
title: "TUI Playbook — the service-agnostic charter for building SG/Send TUIs"
file: 01__tui-playbook.md
author: Architect (Claude)
date: 2026-05-20 (UTC hour 23)
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (v0.2.36 line)
status: GUIDE — reusable. The first thing a new TUI agent reads.
parent: README.md
---

# TUI Playbook

The reusable core. Everything here applies to **any** AWS-service TUI; nothing here is CloudFront-specific. Read it first, then use the brief template (`02`) and idiom catalogue (`03`).

---

## 1. The stance — art of the possible

We are at the **exploration** stage, not the production stage. That changes how you work:

- **Each screen is a learning artefact**, not a product. Its job is to teach us what shape works.
- **Expect to discard.** Some screens will be kept, some dropped, some merged into a better design. That is success, not waste.
- **Bounded effort.** A day or two per screen. Breadth of exploration beats depth of polish.
- **Document negative results.** "The topology view got cluttered past 10 nodes" is as valuable as a win. Capture it.
- **Real data is the point.** A screen that renders real state — even ugly — teaches more than a beautiful mockup of data we don't have.

If you find yourself hardening, abstracting, or building for hypothetical future services, stop — that's the production stage, and we're not there yet.

---

## 2. The architectural pattern (the part that never changes)

### 2.1 Thin over primitives
The TUI is a **rendering layer over existing primitives** (CLI commands / service classes). It **never owns state** — it subscribes to primitive output and displays it. If the TUI needs data the primitives don't expose, the fix is to extend the primitive, not to grow a parallel data model in the TUI. (Mirrors CLAUDE.md rule 19: views have no logic.)

### 2.2 Find the data-source seam
Before designing any screen, answer: **what are the pure read-primitives for this service, and can I render them directly without a heavy backend in the loop?**

The strongest TUIs read the source directly. In the CloudFront reference instance, the seam was that the parsers are pure and ES-independent, so the TUI reads S3 → parse → render with **no Elasticsearch**. Look for the equivalent seam in your service:

```
list/describe primitive  →  fetch/get primitive  →  pure transform (if any)  →  render
```

Keep slow or stateful backends (ES, a provisioning step, a long poll) **out of the live render loop**. They can be optional downstream consumers, never the spine.

### 2.3 One module per TUI
Each TUI is a **separate module** (e.g. `sg-{service}-tui`). The service's CLI/primitives stay exactly as they are — flag-driven, scriptable, agent-friendly. The TUI sits on top and is independently replaceable.

---

## 3. Framework — Textual + Rich, *conditioned*

**Default: Textual + Rich (Python).** Already in-stack, fastest to iterate visual design, mature widgets (DataTable, Tree, Sparkline, ProgressBar), works over the SSH/SSM chain. The single feature that matters most *for this codebase*: **`App.run_test()` — the pilot harness** lets you drive a real app (`pilot.press(...)`) and assert on widget state with **no mocks and no real terminal**, which is exactly the project's no-mocks testing culture. Don't relitigate this per-TUI. Second choice: Bubble Tea + Lipgloss (Go), only if single-binary distribution becomes the priority.

**The recommendation is conditioned on four disciplines** — Textual is a fast-moving, heavy dependency (8.x churns its API between majors), so adopt it *this* way or the bet is unsafe:

1. **Content/view split — non-negotiable.** All content and logic live in **pure functions** (a `*_markup()` string builder, the Type_Safe aggregator/snapshot, the ASCII `Card`) that import **no Textual and no Rich** and are unit-tested on their own. The Textual `App` is a thin shell that polls the source, drops the pure markup into a `Static`, and binds keys. This is what makes the framework *swappable*: if Textual churns or is replaced, the value and tests are untouched.
2. **Lazy + gated, never load-bearing.** Import Textual *inside* the command body, so registering the CLI sub-app never requires it — the rest of the CLI works without Textual installed. View-layer tests `@skipUnless` Textual is importable (exactly as CLI suites gate on typer); the pure layers always run.
3. **Keep it out of the core service deps.** Textual is **operator tooling, not runtime** — do not add it to the main `pyproject.toml` dependencies (the one Docker image runs on Lambda/Fargate and stays lean). Install it where the TUI actually runs, and **pin the major version** given the churn.
4. **Spend it where it pays.** A static dashboard is ~95% Rich (markup into one `Static`); Textual barely earns its keep there. Its real payoff is the **interactive** screens — focus/drill-in navigation, `DataTable`, modal help, live filtering, pause. Reach for Textual's layout/widget machinery on those; don't over-engineer the static screens with it.

---

## 4. The deployment chain (SSM + docker exec) — survival checklist

Every TUI is accessed through: `laptop terminal → SSH/SSM → EC2 → docker exec → container`. The rich experience survives this **only if** these hold. Treat them as design constraints, not afterthoughts:

- **Throttle updates to 5–10 Hz**, never 60. Bursty output over a saturated link feels worse than slower-but-steady.
- **First frame < 100 ms.** The operator already waited through three hops — render "loading" panes immediately.
- **Keyboard-primary.** Every action reachable without a mouse; mouse is enhancement only.
- **Graceful resize.** SIGWINCH must re-layout cleanly; no broken frames.
- **`LANG`/`TERM` set at the container level** (`ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 TERM=xterm-256color`; `apt-get install -y ncurses-term locales`). Do not rely on inheritance through three hops.
- **`docker exec -it`** (both flags) is mandatory or the TUI library sees no TTY and falls back to dumb output.
- **Ship a `…-tui-diagnose` subcommand** that prints `$TERM`, `$LANG`, `tput colors`, a Unicode block test, and a truecolor test, so operators can self-check before reporting issues.

---

## 5. Visual principles (distilled)

1. **Layout encodes information** — related state goes next to each other; spatial relationship is meaning.
2. **Colour is semantic, not decorative** — red = problem, green = good, the same colour means the same thing everywhere.
3. **Sparklines and gauges compress time** — `▁▂▄▆█▅▃` shows a trend that ten timestamped lines would bury.
4. **Unicode block/box characters do the drawing** — `█▓▒░ ▁▂▃▄▅▆▇ ╭╮╰╯ ━┃`.
5. **Status is always visible** — the screen shows current state; you never have to ask.
6. **Help is one keypress away** — `?` shows context-aware keybindings.
7. **Animation conveys information or it doesn't belong** — spinners for async work, a subtle pulse on a changing value; never decorative motion in an operational view.
8. **Partial redraws, not full repaints** — let the framework diff; it's what keeps the chain responsive.

---

## 6. The simulate principle

Where a service involves **transformations or mutations**, make **dry-run a first-class screen**, not a flag buried in a command. Preview the result — for a transform, show the field-diff (adds / changes / drops) and a sample row; for a mutation, show what will change — **before** anything is written. Gate the actual write behind the service's `…_ALLOW_MUTATIONS` env (consistent with `sg aws s3`/`cf`). Simulation is often the highest-value screen because it makes designing the *next* pipeline stage dramatically faster.

---

## 7. The honesty rule

- **Label EXISTS vs PROPOSED everywhere.** A mockup must never imply unbuilt machinery is live.
- **Mark unknowns in the UI**, don't hide them. The CloudFront architecture screen renders `⚠ UNVERIFIED` for wiring it can't confirm rather than drawing a clean line that lies. Copy that pattern.
- **If the data is synthetic, say so on the screen.** A `[SYNTHETIC]` banner is cheap and keeps trust intact.

---

## 8. Definition of done — for an *exploration* screen

A screen is "done enough" when:
- it **runs** as a command;
- it reads **real data** (or is clearly labelled synthetic);
- it **teaches** something — answers a real question at a glance;
- the agent has **written notes** on what worked, what didn't, and what they'd change.

It does **not** need: production polish, exhaustive error handling, full test coverage of the rendering, or multi-service abstraction. (It *does* follow Type_Safe rules for any new primitives it introduces.)

---

## 9. The promotion conversation ("the sixth conversation")

After ~a week of using the prototypes, hold the decision: which screens become tabs of a canonical `sg-{service}-tui`, which stay standalone commands, which get dropped, and which get merged into a better shape that absorbs the best of several. This conversation happens **after** the screens exist and have been used — never before. That's how the art of the possible turns into a product.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
