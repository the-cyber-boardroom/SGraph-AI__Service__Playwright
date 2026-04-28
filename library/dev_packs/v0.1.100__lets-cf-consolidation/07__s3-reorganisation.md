# 07 — S3 Reorganisation (Part A in this slice; Part B deferred)

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Document the new `lets/` workspace S3 layout (Part A, in this slice) and inventory the future cleanup work for the 58 hardcoded `cloudfront-realtime` literal references (Part B, deferred to a separate slice).

This doc exists to prevent two failure modes:

1. **Sonnet quietly bundling Part B into v0.1.101** — the refactor would couple the consolidation feature to a code-cleanup task and significantly inflate the blast radius and review surface.
2. **The Part B work being lost to memory** — capturing it now means it's a known follow-up, not a forgotten technical debt.

---

## Sections to include

### 1. Part A — what THIS slice does (additive only)

The new `lets/` prefix is introduced under the existing `745506449035--sgraph-send-cf-logs--eu-west-2` bucket. Source data stays where Firehose writes it (`cloudfront-realtime/`).

```
   s3://745506449035--sgraph-send-cf-logs--eu-west-2/
   ├── cloudfront-realtime/      ← UNTOUCHED — Firehose target
   └── lets/                     ← NEW — LETS workspace
       └── raw-cf-to-consolidated/
           ├── lets-config.json
           └── 2026/04/27/
               ├── manifest.json
               └── events.ndjson.gz
```

All NEW writes go here. All NEW reads (`events load --from-consolidated`) come from here. Existing reads from `cloudfront-realtime/` are untouched.

**Bucket policy / IAM impact:** the existing IAM policy already grants `s3:GetObject` and `s3:PutObject` on `arn:aws:s3:::745506449035--sgraph-send-cf-logs--eu-west-2/*` (i.e. all keys). The new prefix is a no-op for IAM. If IAM is more granular than that, this doc lists the policy lines that need extending.

**Lifecycle:** the existing lifecycle rule (if any) on `cloudfront-realtime/` does not apply to `lets/` — the consolidated artefacts have their own lifecycle, defined here. Recommendation: keep consolidated artefacts forever (they're cheap and they're our parsed-and-classified state); add a separate lifecycle rule only if storage cost grows enough to matter.

### 2. Part B — the 58-occurrence refactor (NOT in this slice)

The following files reference `cloudfront-realtime` as a hardcoded string literal. Refactoring them is a separate slice.

**Source files (5):**

| File | Occurrences | Type |
|------|-------------|------|
| `scripts/elastic_lets.py` | TBD | CLI default |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Events__Loader.py` | TBD | Default prefix |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/schemas/Schema__Inventory__Load__Request.py` | TBD | Default prefix |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/Inventory__Loader.py` | TBD | Default prefix |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/sg_send/service/SG_Send__Date__Parser.py` | TBD | Date parsing root |

**Test files (9):** all in `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/...`. These are golden-fixture tests with real CloudFront S3 keys. Refactoring them needs care — the prefix part of the key must change, the rest of the key (the timestamp + UUID) must stay.

**Total: 58 occurrences across 14 files.**

(Sonnet — please run `grep -rn "cloudfront-realtime" --include="*.py" .` to populate the exact occurrence counts in this table during Phase 0.)

### 3. The proposed Safe_Str primitive (Part B preview, not implemented here)

```python
# sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/primitives/Safe_Str__CF__Source__Prefix.py
class Safe_Str__CF__Source__Prefix(Safe_Str):
    regex          = re.compile(r"^[a-z][a-z0-9-]*/?$")
    max_length     = 200
    DEFAULT_VALUE  = 'cloudfront-realtime/'
```

Used as the default for `Schema__Inventory__Load__Request.prefix`. CLI override: `--source-prefix`. Env var override: `SP_CF_SOURCE_PREFIX`.

The Part B refactor:
1. Adds the new primitive
2. Replaces every literal `'cloudfront-realtime/'` and `"cloudfront-realtime/"` with `Safe_Str__CF__Source__Prefix.DEFAULT_VALUE`
3. Updates test fixtures to use the same constant
4. Adds a CLI flag and env var override on every command that accepts a prefix
5. Documents the override in the CLI help

Estimated effort for Part B: 1 day with care; 0.5 day rushed (and the rushed version will leak literals).

### 4. Why Part B is deferred

| Reason | Detail |
|--------|--------|
| **Decoupling the feature from cleanup** | v0.1.101 ships a measurable architectural win (the C-stage). Bundling the refactor would make the PR diff dominated by find-and-replace noise, hiding the architectural change from review. |
| **Test-fixture risk** | The 9 test files use real CloudFront S3 keys with the prefix embedded in the key. Refactoring needs care to preserve the rest of each key. Better as its own focused PR. |
| **Composition** | Once the orchestrator (v0.1.102) lands and wants to be parameterisable for other source buckets, the refactor becomes more obviously useful — and will be easier to specify against a concrete need. |

### 5. Why Firehose stays where it is (out of scope for both Part A and Part B)

The user raised whether to also rename Firehose's destination from `cloudfront-realtime/` to something under `lets/`. Architect's recommendation: **not in this slice and not in Part B either.** Reasons:

1. The S3 keys are timestamp-immutable — renaming the prefix requires recreating the Firehose delivery stream with downtime risk.
2. The 58 hardcoded references in tests are golden fixtures with real-world filenames; renaming the live prefix would invalidate them even after the Part B refactor.
3. The `lets/` workspace owns the **outputs** of LETS workflows. Source data lives wherever it naturally lives — Firehose writes to `cloudfront-realtime/`, and that's a source-of-truth boundary, not a workflow-output boundary.

A separate operational decision (post v0.1.102) can revisit this: should Firehose write under `lets/raw-cf/` from day one for **greenfield buckets**, with everything else as a derivative? Likely yes. But not for this bucket, not now.

### 6. Diagrams

Include the same `s3://...` tree diagram from the README §"S3 layout and config-at-folder-root" — repeat it here so this doc stands alone.

---

## Source material

- README §"S3 layout and config-at-folder-root" (decisions #2 and #5)
- README §"S3 reorganisation" (the Part A / Part B split)
- The grep output that yielded "58 occurrences across 14 files" — Sonnet to run fresh during Phase 0 and populate the exact counts
- Architect's reasoning in the chat thread that produced this brief (paraphrased into the "Why deferred" section)

---

## Target length

~80–120 lines.
