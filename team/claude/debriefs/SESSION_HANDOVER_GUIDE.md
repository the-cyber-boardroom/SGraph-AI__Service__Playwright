# Session Completion & Handover Debrief — Guidelines

**Audience:** Any Claude agent wrapping up a session in this repo.
**Trigger phrase from the user:** "wrap up this session" / "write a session debrief" / "I want to continue this in a new Claude Code session."

This guide is the meta-template. The user should not need to spell out what a "good debrief" looks like every time — just say "wrap up" and follow this.

---

## What to produce

When asked to wrap up, produce **two artefacts**:

1. **The session debrief** — one Markdown file, dated, in `team/claude/debriefs/`.
2. **The index entry** — one row in `team/claude/debriefs/index.md`, top of the table.

Optionally a third if relevant:
3. **A follow-up plan** — `team/comms/plans/v{next-version}__{slice-name}.md` for the next big slice, **only if** the next slice is concrete and the work is sized for one PR. Don't write speculative plans.

---

## Where things live (so the next agent can find them)

| Artefact            | Path                                                           |
|---------------------|----------------------------------------------------------------|
| Debriefs            | `team/claude/debriefs/YYYY-MM-DD__{slug}.md`                   |
| Debrief index       | `team/claude/debriefs/index.md` (newest first, table format)   |
| Plans               | `team/comms/plans/v{version}__{slice-name}.md`                 |
| Reality doc (sg-compute) | `team/roles/librarian/reality/sg-compute/index.md`        |
| Reality doc (Playwright) | `team/roles/librarian/reality/v{version}__what-exists-today.md` |
| Decisions log       | `library/reference/v{version}__decisions-log.md`               |
| Cross-role briefs   | `team/comms/briefs/`                                           |
| **NEVER write to**  | `team/humans/dinis_cruz/briefs/` or `…/debriefs/` (HUMAN-ONLY) |

---

## Slug naming

`YYYY-MM-DD__{area}-{slice-name-kebab}.md`

Examples:
- `2026-05-10__sg-compute-spec-cli-builder-and-ami.md` — multi-area, kebab-case
- `2026-05-05__t2-7b__docstring-sweep.md` — task-numbered slice
- `2026-05-05__bv2.11__lambda-cutover.md` — backlog-vehicle slice

When in doubt: date + the most specific scope you worked on.

---

## Required sections in the debrief

Mirror the layout of `2026-05-10__sg-compute-spec-cli-builder-and-ami.md` (the canonical example). The required structure:

### 1. Header
- **Date** (today's date as known by the harness — `2026-MM-DD`)
- **Status** — `COMPLETE`, `PARTIAL` (with gaps table appended), or `WIP`
- **Versions shipped** — what `version` files moved
- **Commits** — table of `<hash> | <one-line>`. Use `git log --oneline --since='N days ago'` to recover them
- **Branch** — and whether it is merged to `dev`

### 2. TL;DR for the next agent
3–5 numbered bullets. Optimised for an agent who has 30 seconds before they have to make a decision. Should answer:
- What is the most important thing they need to know?
- What is unmerged / open / pending decision?
- What are the must-do follow-ups?
- What is mandatory before merge / ship?

### 3. What was done
Sub-section per major chunk of work. **Include commit hashes** so the next agent can `git show <hash>` for exact context.

### 4. Failure classification (mandatory, per CLAUDE.md rule 27)
For each notable failure during the session, classify it as:
- **Good failure** — surfaced early, caught by tests, informed a better design.
- **Bad failure** — silenced, worked around, or re-introduced. **A bad failure is an implicit follow-up request.**

If there were no failures worth mentioning, write "No failure events this session." Do NOT skip the section silently.

### 5. Lessons learned
The "things I now know that I didn't before this session." Group by area (Type_Safe, typer, AWS, etc.). The next agent reads this to avoid re-discovering bugs.

### 6. Files changed this session
Group as **New files**, **Modified files (by package)**, **Tests**. Don't enumerate every file in a 50-file rename — name the directories. **Always** be exact about new files (so the next agent can `read` them).

### 7. Test status
- Which test suites pass
- Which fail (with classification: pre-existing on `dev` vs introduced this session)
- Which fail at collection time (env gaps) — note for the next agent so they don't waste time

### 8. Open questions
Decisions that need user input before merge / next session. Each item: question + recommended option + alternatives. The user should be able to answer with one word.

### 9. Follow-ups (sized for next session)
Three buckets:
- **Must-do before merging this branch** — checklist
- **Next big slice** — with reference to plan file if written
- **Smaller items / opportunistic cleanup** — paragraph form

### 10. Where to start (if continuing this work)
A reading order: which files / docs in what order. Include "don't bother reading X unless Y comes up" — saves the next agent context budget. Include "critical files to NOT touch unless deliberately changing the contract."

### 11. What to take into account next session
The non-obvious stuff: branch state, AWS region the user is on, cost ceilings, harness limitations. Anything that would surprise an agent who started fresh.

**ALWAYS** include a "branch handover" sentence: each session has its own `claude/{description}-{session-id}` branch (CLAUDE.md rule 30). The next agent must be **aware of** the previous session's branch (it carries unmerged work) but **must NOT commit onto it** — they branch off it (or off `dev` if it has merged). Spell out the exact `git checkout -b` command in the debrief so there's no ambiguity.

---

## How to gather the material (mechanical steps)

Before writing, run these in order:

```bash
# Session commits (use whatever range covers your session)
git log --oneline --since='2 days ago'                         # adjust window
git log --stat <oldest-session-hash>..HEAD                     # full diff stats

# Current state
git status --short
git branch --show-current
cat sg_compute/version  sgraph_ai_service_playwright/version  # whichever applies
git diff origin/dev...HEAD --stat                              # what's unmerged

# Test baseline (so you can report which failures are pre-existing)
git stash && python -m pytest <suspect-test> -q ; git stash pop
```

For long sessions where the early conversation is no longer in context, also:

```bash
ls /root/.claude/projects/<this-project-slug>/ -t | head -3    # session transcripts
```

The transcript file is the source-of-truth for "what did the user actually ask for" if your context has been compacted.

---

## Index entry format

Single row at the top of the table. Columns:

```
| YYYY-MM-DD | `hash1` `hash2` ... | **Headline (8–15 words)** — Detail paragraph (60–120 words). State unmerged status, must-dos, gotchas. | `filename.md` |
```

Style rules:
- Headline in bold, em-dash, then the paragraph
- Commits as code spans, space-separated
- **Always** mention if the branch is unmerged
- **Always** mention any "mandatory" follow-up (e.g. "live AWS smoke required")
- Match the writing density of the surrounding rows — they're quite information-dense

---

## What NOT to do

1. **Do not write a chronological diary.** The debrief is for the next agent's decision-making, not a log of what you did when. Lead with consequences, then explanations.
2. **Do not write speculative plans.** If the next slice is unclear, list it under "follow-ups" without a plan file. Plans are written when the work is concrete and sized for a single PR.
3. **Do not skip Failure Classification.** CLAUDE.md rule 27 is non-negotiable. If you weren't sure, write "Good failure — none flagged" / "Bad failure — none flagged" rather than omitting.
4. **Do not invent commit hashes.** Use `git log` output. If you don't have a hash yet (committed locally but not pushed, or commit pending), write `*(pending)*` matching the convention used in the index.
5. **Do not write to `team/humans/dinis_cruz/`.** Those folders are HUMAN-ONLY (CLAUDE.md rule 23/24). Agent outputs go to `team/claude/debriefs/`.
6. **Do not update the reality doc as part of the debrief.** That is the Librarian's role — flag it as a follow-up unless the user explicitly asked for it.
7. **Do not commit and push** the debrief without confirming with the user first if the branch is not yet a "wrap-up" branch. Often the user wants to review the debrief in their editor before it is pushed.

---

## Quality bar

A good handover debrief lets the next agent:

1. Know within 30 seconds what state things are in.
2. Find the canonical reference files within 2 minutes.
3. Decide what to work on next without asking the user.
4. Avoid every bug that was already surfaced and fixed in this session.

If you can't honestly say "yes" to all four, the debrief needs another pass.

---

## Trigger checklist (for the user)

When the user says "wrap up this session" / similar, you should:

- [ ] Run the git / state-gathering commands above
- [ ] Write the debrief at `team/claude/debriefs/YYYY-MM-DD__<slug>.md`
- [ ] Add the index row at the top of `team/claude/debriefs/index.md`
- [ ] Optionally: write a follow-up plan if the next slice is concrete
- [ ] Stage + commit the new files (don't auto-push — let the user review)
- [ ] Tell the user: file paths created, branch state, and one sentence on the next agent's first move

That's it. Done.

---

## Suggested user prompt for next time

If the user wants the shortest possible trigger:

> "wrap up this session"

If they want to be explicit:

> "write a session handover debrief per `team/claude/debriefs/SESSION_HANDOVER_GUIDE.md`"

If they want to include a follow-up plan:

> "wrap up this session and write a plan for the next phase"
