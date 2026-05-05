# BV — `GET /api/specs/{spec_id}/readme` endpoint

⚠ **Backend dependency** — filed by frontend during T2.2 review. The frontend's `<sg-compute-spec-detail>` component (T2.2 commit `dc703ed`) ships with a known-broken anchor link to a backend endpoint that doesn't exist yet.

## What's needed

A new endpoint on `Fast_API__Compute`:

```
GET /api/specs/{spec_id}/readme
```

Returns the spec's `README.md` content as `text/markdown` (or `text/plain`) — whatever the dashboard's renderer expects.

## Tasks

1. **Add a route handler** to `Routes__Compute__Specs` (or a new `Routes__Compute__Specs__Readme` if cleaner):
   - Look up the spec via `self.registry`.
   - Resolve `sg_compute_specs/<spec_id>/README.md` from the spec's package data.
   - Read the file content; return as response with appropriate `Content-Type`.
   - 404 if the spec has no README (most won't yet — that's fine).
2. **Type_Safe schema for the response** — `Schema__Spec__Readme` with `content: Safe_Str__Markdown` and `last_modified: Safe_Str__ISO_Datetime`. Or return raw text body — Architect call.
3. **Tests** — round-trip read of an existing README; 404 for a spec without README.
4. **Frontend coordination** — once shipped, ping the frontend dev to flip the spec-detail's "broken anchor" warning to a real link.

## Acceptance criteria

- `GET /api/specs/firefox/readme` returns 200 with the README content (assuming firefox has one).
- 404 for specs without README.
- Cached appropriately (long Cache-Control once shipped — README is immutable per spec version).
- Frontend can consume it without further backend changes.

## "Stop and surface" check

If a spec has its README in an unusual location: **STOP**. The rule should be `<spec>/README.md` — uniform across all specs. If a spec has it elsewhere, that's a spec-layout violation; surface to Architect.

## Source

Frontend T2.2 review (2026-05-05 14:00); the frontend dev did NOT file this brief at the time of T2.2 — that's a process gap addressed by this brief. Subsequent FE patches assume this brief is in flight.
