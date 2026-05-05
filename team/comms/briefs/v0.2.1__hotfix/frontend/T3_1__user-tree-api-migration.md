# T3.1 — Migrate `user/user.js` to `/api/*` (FV2.2 only did admin tree)

⚠ **Tier 3 — integration cleanup.** Standalone PR.

## What's wrong

FV2.2 brief was scoped to migrate the **admin** tree to the new `/api/*` URLs. The user tree (`sgraph_ai_service_playwright__api_site/user/user.js:76-77`) was missed. It still calls:

- `/catalog/types`
- `/catalog/stacks`

unconditionally with no `useLegacyApiBase` toggle. The user UI is a regression risk on every backend change to `/legacy/*`.

## Tasks

1. Find the calls in `user/user.js:76-77`.
2. Replace with `/api/specs` and `/api/nodes` respectively.
3. Update field-name consumers in `user/user.js` — `type_id` → `spec_id`, `stack_name` → `node_id`, etc.
4. Verify the user page still renders + functions correctly in a browser.
5. If the user page has its own components (`sg-compute-user-pane` etc.), sweep those too.

## Acceptance criteria

- `grep -rn "/catalog/" sgraph_ai_service_playwright__api_site/user/` returns zero hits.
- `grep -rn "stack_name\|type_id" sgraph_ai_service_playwright__api_site/user/` returns zero hits in active code paths.
- User page renders correctly with no console errors.

## Live smoke test

Open the user page in a browser. Network tab: `/api/specs` + `/api/nodes` calls. No `/catalog/*` calls. Spec list renders.

## Source

Executive review Tier-3; frontend-early review §"Top integration issue (FV2.2 scope gap)".
