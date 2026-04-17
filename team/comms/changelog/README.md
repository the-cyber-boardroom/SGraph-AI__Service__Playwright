# Changelog

Dated entries that record what shipped, what broke, and what we learned. Uses the **good failure / bad failure** convention imported from SGraph-AI__App__Send.

---

## Structure

`team/comms/changelog/YY-MM-DD/v{version}__{description}.md`

---

## Entry Template

```markdown
# v{version} — {title} — {date}

## What shipped
- ...

## What was deferred
- ...

## Good failures
- {something that broke loudly + early; caught by tests; informed a better design}

## Bad failures
- {something that was silenced or worked around; must be fixed, not buried}

## Commit(s)
- {hash} — {message}
```

---

## Rules

1. **One entry per slice.** Not per commit, not per day. The slice is the unit.
2. **Good failures are celebrated.** Name them plainly; they save future time.
3. **Bad failures are flagged.** A bad failure entry is an implicit request for follow-up work.
4. **Reference the reality doc.** Every slice that changes what exists must point to the reality-doc update commit.
