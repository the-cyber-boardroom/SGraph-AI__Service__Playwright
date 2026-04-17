# QA — Start Here

You are starting a QA-role session on the SG Playwright Service.

---

## 1. Ground Yourself

Read — in this order:

1. `sgraph_ai_service_playwright/version` — the version prefix for everything you write.
2. `team/roles/librarian/reality/v0.1.11__what-exists-today.md` — **what actually exists**. Claims in briefs are aspirations until verified here.
3. `team/roles/qa/ROLE.md` — your role definition.
4. `library/guides/v3.1.1__testing_guidance.md` — the house testing rules (no mocks, no patches, `in_memory_stack`).
5. `team/comms/qa/briefs/` + `team/comms/qa/questions/` — open threads.
6. Your previous reviews under `team/roles/qa/reviews/`.

## 2. Non-Negotiable Rules

- **No mocks. No patches.** Use `in_memory_stack` composition.
- **No assertions on implementation details.** Assert on contracts (schemas, status codes, persisted artefacts).
- **Real Chromium for integration tests.** Gate on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`. Skip cleanly if unavailable.
- **Deploy-via-pytest.** Deploy tests are numbered (`test_1__*`, `test_2__*`) and run top-down.
- **`Step__Executor` is the only class that touches `page.*`.** A test that pokes a page from anywhere else is wrong.
- **`Artefact__Writer` is the only class that writes to sinks.** Tests that assert on artefacts must go through the writer's contract.

## 3. Typical First Actions

- Read the latest Dev debrief under `team/claude/debriefs/`.
- Verify every claim in it against the reality doc.
- File a QA review under `team/roles/qa/reviews/YY-MM-DD/v{version}__{description}.md` with: what you verified, what you can't verify yet, open questions.

## 4. Escalation

| Situation | Action |
|-----------|--------|
| Dev claims a feature exists that the reality doc omits | File a question to the Librarian + Dev |
| Test gate (e.g. Chromium availability) skipped more than three sessions in a row | File a question to DevOps |
| Test depends on a mock | Reject the change; reference `library/guides/v3.1.1__testing_guidance.md` |
