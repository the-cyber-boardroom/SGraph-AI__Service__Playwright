# Phase B · Step 5f.4a — `OpenSearch__Launch__Helper`

**Date:** 2026-04-26.
**Commit:** `0a09731`.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split/04__sp-os__opensearch.md`.
**Predecessor:** Step 5f.3 (user-data with install steps).

---

## What shipped

`OpenSearch__Launch__Helper.py` (~40 lines) — single-purpose helper for the `run_instances` call. Kept separate from `OpenSearch__Instance__Helper` (which is read-only + terminate) so the launch surface is reviewable in isolation.

```python
run_instance(region, ami_id, security_group_id, user_data, tags,
             instance_type=DEFAULT_INSTANCE_TYPE, instance_profile_name=None) -> str
```

Behaviour locked by test:
- Base64-encodes UserData (AWS rejects raw bytes)
- `MinCount=MaxCount=1` (single-node OS stack)
- `SecurityGroupIds`, `TagSpecifications` wired
- `IamInstanceProfile` attached only when `instance_profile_name` is set (sp os reuses the playwright-ec2 profile when unset)
- Empty `Instances` response → `RuntimeError`
- Boto failures propagate (no silent swallow)

`DEFAULT_INSTANCE_TYPE = 't3.large'` — 2 vCPU / 8 GB. Cheaper than the elastic m6i.xlarge default; OpenSearch + Dashboards fit on 8 GB for ephemeral dev stacks.

## Tests

11 tests with a real `_Fake_Boto_EC2` subclass (no mocks):
- Returns instance_id (happy path)
- UserData base64 round-trips correctly
- SG / tags / instance_type / profile attached
- `MinCount=MaxCount=1` pinned
- Empty response raises; boto failure propagates

## Files changed

```
A  sgraph_ai_service_playwright__cli/opensearch/service/OpenSearch__Launch__Helper.py
A  tests/unit/sgraph_ai_service_playwright__cli/opensearch/service/test_OpenSearch__Launch__Helper.py
```
