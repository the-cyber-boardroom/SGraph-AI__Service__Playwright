# Specifications — Definitive

These are the **definitive** specs for the SG Playwright Service. If code and spec disagree, the spec wins unless a decision has been logged overriding it.

---

## Catalogue

| Document | Lines | Content |
|----------|------:|---------|
| [`v0.20.55__schema-catalogue-v2.md`](v0.20.55__schema-catalogue-v2.md) | 1439 | Every `Type_Safe` schema, enum, Safe_* primitive, and collection subclass |
| [`v0.20.55__routes-catalogue-v2.md`](v0.20.55__routes-catalogue-v2.md) | 1234 | All 25 routes, 12 service classes, registration pattern, step dispatch |
| [`v0.20.55__ci-pipeline.md`](v0.20.55__ci-pipeline.md)                 | 1161 | CI jobs, Docker infrastructure classes, deploy-via-pytest layout |

---

## Related

- **Research behind the specs:** [`../research/`](../research/) — base-image selection, prior art, OSBot-Playwright deep dive
- **Phased delivery:** [`../../roadmap/phases/`](../../roadmap/phases/)
- **Reality document (what exists today):** [`../../../team/roles/librarian/reality/`](../../../team/roles/librarian/reality/)

---

## Changing a Spec

1. Propose the change via a review in `team/roles/architect/reviews/MM/DD/`.
2. Update the spec file in place (bump the version prefix to the current service version).
3. Log the decision in [`../../reference/`](../../reference/) with the rationale.
4. Update the reality document to reflect any code impact.
5. Notify the Librarian so the master index picks up the change.
