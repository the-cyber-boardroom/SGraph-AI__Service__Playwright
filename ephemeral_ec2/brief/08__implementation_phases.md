# Ephemeral EC2 — Implementation Phases

## Phase 0 — Repo structure & package skeleton  [no AWS, no tests yet]

Create the folder layout described in `03__package_structure.md`:
- `ephemeral_ec2/__init__.py`
- `ephemeral_ec2/helpers/` tree (empty `__init__.py` files only)
- `ephemeral_ec2/stacks/open_design/` tree
- `ephemeral_ec2/stacks/ollama/` tree (stub)
- `ephemeral_ec2__tests/` mirror tree

Deliverable: `import ephemeral_ec2` works; all folders present.

---

## Phase 1 — Helpers layer  [no AWS, fully testable]

Implement all classes in `helpers/` with fake-friendly design:
every helper takes its AWS client as a constructor argument so tests
can substitute a fake without patches.

Order:
1. `EC2__Tags__Builder` — pure dict construction, no AWS
2. `Section__*` classes — pure string rendering, no AWS
3. `EC2__Stack__Mapper` — pure dict → schema, no AWS
4. `Stack__Name__Generator` — pure random, no AWS
5. `Caller__IP__Detector` — HTTP call, easy to fake
6. `EC2__AMI__Helper` — SSM call, fake-able
7. `EC2__SG__Helper` — EC2 calls, fake-able
8. `EC2__Launch__Helper` — EC2 RunInstances, fake-able
9. `EC2__Instance__Helper` — DescribeInstances, fake-able
10. `Health__HTTP__Probe` — HTTP GET, fake-able
11. `Health__Poller` — composes items 9 and 10

Tests for every class in `ephemeral_ec2__tests/helpers/`.
All tests pass with no AWS credentials.

---

## Phase 2 — Open Design stack (cold boot)  [no AWS in tests]

Implement `stacks/open_design/` in order:

1. `Schema__Open_Design__*` — all four schemas
2. `Open_Design__Stack__Mapper` — extend `EC2__Stack__Mapper`
3. `Open_Design__User_Data__Builder` — compose sections, render bash
4. `Open_Design__Service` — wire helpers, implement five mandatory methods
5. CLI `__init__.py` + `Renderers.py`

Tests:
- `test_Open_Design__User_Data__Builder` — assert script contains key strings
  (`pnpm install`, `open-design.service`, `proxy_buffering off`, shutdown timer)
- `test_Open_Design__Service` — create/delete with fake helpers; assert events emitted

At end of phase 2: `ec2 open-design create --region eu-west-2 --wait` works end-to-end
against real AWS. Boot time ~8 min cold (acceptable for validation).

---

## Phase 3 — Open Design AMI bake

Implement `bake-ami` command and `EC2__AMI__Helper.create_ami()`.

Baked AMI includes: AL2023 base, Docker, Node 24, pnpm, cloned open-design repo,
completed `pnpm install + build`.

After bake: `ec2 open-design create --fast-boot --from-ami <id> --wait`
targets < 60 s to health-ready.

---

## Phase 4 — Ollama stack (CPU first)

Implement `stacks/ollama/` same order as Phase 2. Use a CPU instance type
(c7i.4xlarge) and a small model (qwen2.5-coder:7b) for initial validation.
No GPU driver complexity yet.

Tests follow the same pattern as open-design tests.

End of phase: two-stack workflow works:
```bash
ec2 ollama create --instance-type c7i.4xlarge --model qwen2.5-coder:7b --wait
ec2 open-design create --ollama-ip <private-ip> --open
```

---

## Phase 5 — Ollama GPU support

Add `Section__Nvidia__Drivers` user-data section.
Test against g4dn.xlarge with Llama 3.3 70B q4.
Add GPU validation in `Open_Design__Service.create_stack()`.
Implement Ollama AMI bake (drivers + model pre-pulled).

---

## Phase 6 — Launch Template support (ASG path)

Add `create-launch-template` command to both stacks.
Mirrors the Firefox launch-template implementation in the existing CLI.
Enables ASG-based scaling of open-design instances behind an ALB.

---

## Phase 7 — PyPI extraction

- Move `ephemeral_ec2/` to a new standalone repository
- Move `ephemeral_ec2__tests/` alongside it
- Publish `ephemeral-ec2` to PyPI
- Update `sgraph_ai_service_playwright__cli/` to depend on the published package
  (or keep vendored copy — TBD)

---

## Testing philosophy (all phases)

**No mocks. No patches.** Fakes are explicit subclasses or simple objects.

Every fake AWS collaborator is a class defined in the test file or a shared
`conftest.py` at `ephemeral_ec2__tests/`. Fakes record calls for assertion.

Integration tests (real AWS) are gated on `EPHEMERAL_EC2__INTEGRATION=1`
environment variable and run separately from the unit suite.

---

## Key risks and mitigations

| Risk                                    | Mitigation                                               |
|-----------------------------------------|----------------------------------------------------------|
| pnpm build time (3–8 min cold)          | AMI bake in Phase 3; fast-boot flag                      |
| open-design upstream API changes        | Pin to a git ref; test user-data for key strings         |
| GPU driver install complexity on AL2023 | Phase 5 deferred; CPU path validates everything first    |
| open-design SSE breaking with nginx     | `proxy_buffering off` + integration smoke test           |
| Ollama model size vs VRAM budget        | Instance-type / model-size validation table in service   |
| User-data size limit (16 KB raw)        | gzip+base64 brings 13KB → ~4KB; validated in unit test   |
