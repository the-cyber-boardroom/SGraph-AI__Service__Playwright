# Librarian — Activity Log

**Format:** `Date | Version | Reviews / domain updates | One-line summary`

The session-continuity record. Each entry is one line. Detail lives in the linked review or in `reality/changelog.md`.

Read the latest entry at the start of every session before reading [`DAILY_RUN.md`](DAILY_RUN.md).

---

## 2026-05

| Date | Version | Reviews / domain updates | Summary |
|------|---------|--------------------------|---------|
| 2026-05-02 | v0.1.140 | `reality/index.md` (NEW), `reality/changelog.md` (NEW), `reality/README.md` (rewritten), `reality/host-control/` (NEW domain — pilot), `DAILY_RUN.md` (NEW), this log (NEW) | Reality refactor: introduced 10-domain fractal tree, migrated `host-control/` as pilot, seeded daily-run backlog with B-001 … B-012. |
| 2026-05-17 | v0.2.25 | `reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md` (NEW) | Researched sgai-send + sgai-tools librarian patterns; audited reality fragmentation, brief sprawl (4 homes), and oversized docs; proposed 7-kind ontology + taxonomy with phased migration plan (M-001..M-012). Non-destructive; awaits human ratification. |
| 2026-05-17 | v0.2.25 | proposal §3.1, §3.6, §7 (REVISED) | Merged `origin/dev` (sg_compute/version deleted, confirms Q1). Ratifications Q1–Q6 + catalogue concern recorded. Split naming into Pattern A (live, stable filename, frontmatter `as_of`) and Pattern B (versioned snapshot); rewrote §3.6 so live catalogue shards use stable filenames with `_snapshots/v{X.Y.Z}/` for periodic freezes — eliminates rename churn on every version bump. |
| 2026-05-17 | v0.2.25 | M-001..M-007 EXECUTED across 8 commits (~85 files added/moved/rewritten) | Full ontology rollout in one session. Phase 1: CLAUDE.md pointer fixes, catalogue README refresh, NEW `verified-by.md` + `ids/README.md`. Phase 2: `_archive/` for old reality monoliths + `v0.1.31/`; 9 domain indexes + `sg-compute/` split into 7 sub-files; `proposed/index.md` for all 11 domains. Phase 3: `briefing/`→`onboarding/`, `sg_compute/brief/`→`team/comms/`; 8 live catalogue shards + first `_snapshots/v0.2.25/`; `v0.20.55__schema-catalogue-v2.md` and `__routes-catalogue-v2.md` split into cover sheets + 4 parts each; H1 `═══` banners stripped from 3 spec covers. Reality index Status table now reports "11 of 11 migrated"; Migration shim section deleted. New follow-up IDs minted: M-013 (endpoint-count discrepancy), M-014 (VERIFY markers in 4 domains post-BV2.11/BV2.12), M-015 (19 broken links). |
| 2026-05-17 PM | v0.2.28 | Sync `origin/dev` (FF, 94 commits) + intake | Fast-forwarded the branch to `759dfaa` — no conflicts since my ontology commits were already in dev's history. Root `version` → v0.2.28. v0.2.29 work-stream (Foundation + 8 `sg aws` slices: s3/ec2/fargate/iam-graph/bedrock/cloudtrail/creds/observe) shipped with reality docs already in place (7 new `cli/aws-*.md` files + `cli/aws.md` umbrella). Librarian intake: changelog block added covering the v0.2.29 landings; `as_of` bumped on all 8 catalogue shards; reality master index version stamped to v0.2.28; verified-by paragraph appended. Minted `INC-004` (regression where Foundation follow-up overwrote Slice B/C/D CLI with `NotImplementedError`) and `INC-005` (direct `boto3` usage spread to 6 slices / 9 client files — CLAUDE.md rule 13 violation, Architect H-1 flagged HIGH). Deferred: M-016 (cut next catalogue `_snapshots/v0.2.28/`), refresh of `findings.md` with new line counts. |

---

## Entries before 2026-05-02

No formal log was kept before the daily-run system was introduced. For session history pre-2026-05-02, read `git log --author="Librarian" -- team/roles/librarian/` or the version-stamped monoliths under `reality/`.
