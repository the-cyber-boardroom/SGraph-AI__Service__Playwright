---
title: "03 — Delta: brief / lab-brief vs project rules"
file: 03__delta-from-lab-brief.md
author: Architect (Claude — code-web session)
date: 2026-05-17 (UTC hour 00)
parent: README.md
---

# 03 — Delta from brief & lab-brief

The v2 brief and the lab-brief are good designs, but neither was written against an open copy of `.claude/CLAUDE.md`. This file lists every place the brief or lab-brief proposes a shape that violates a project rule, and gives the compliant rewrite Dev should use.

The first half is **brief deltas** (corrections to `/tmp/vault-publish-brief/`). The second half is **lab-brief deltas** (corrections to `team/humans/dinis_cruz/briefs/05/17/from__claude-web/lab-brief/`) — but the lab-brief is **out of the v2 vault-publish critical path**; it is treated as a parallel sibling track, not as part of this plan's deliverables.

---

## A. Brief deltas (`/tmp/vault-publish-brief/`)

### A.1 Schema fields use raw `str` / `bool` / `int` / `dict`

**Brief example** ([`03 §3.5`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md), [`04 §2`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md), [`03 §5.3`](file:///tmp/vault-publish-brief/03__sg-compute-additions.md)):

```python
class Schema__Vault_App__Stop__Response(...):
    name              : str
    instance_id       : str
    stopped           : bool
    dns_record_deleted: bool
    elapsed_ms        : int

class Schema__Lambda__Deploy__Request(...):
    name              : str
    code_path         : str
    handler           : str
    runtime           : str = 'python3.12'
    memory            : int = 512
    env               : Dict__Str__Str
    ...
```

**Violates CLAUDE.md rule #2** ("Zero raw primitives — no `str`, `int`, `float`, `list`, `dict` as attributes").

**Compliant rewrite:**

```python
# sg_compute_specs/vault_app/schemas/Schema__Vault_App__Stop__Response.py
class Schema__Vault_App__Stop__Response(Type_Safe):
    name              : Safe_Str__Stack_Name              # already exists / new under vault_app/primitives/
    instance_id       : Safe_Str__EC2__Instance_Id        # new under sg_compute or vault_app/primitives/
    stopped           : bool                              # `bool` is allowed (it's not in the forbidden list)
    dns_record_deleted: bool
    elapsed_ms        : Safe_Int__Duration_Ms             # new under shared primitives
```

For Lambda:

```python
class Schema__Lambda__Deploy__Request(Type_Safe):
    name                : Safe_Str__Lambda__Name
    code_path           : Safe_Str__Filesystem_Path
    handler             : Safe_Str__Lambda__Handler       # 'module:func' shape
    runtime             : Enum__Lambda__Runtime           # not raw string — see A.2
    memory              : Safe_Int__Lambda__Memory_Mb
    timeout             : Safe_Int__Lambda__Timeout_Sec
    env                 : Type_Safe__Dict__Safe_Str__Safe_Str   # NOT raw `dict[str, str]`
    add_osbot_utils     : bool
    add_osbot_aws       : bool
    container_image_uri : Safe_Str__ECR__Image_Uri
```

The same correction applies to every `Schema__*` sketch in the brief. Dev must NOT take the brief's example literally; replace every bare type with the right `Safe_*` / `Enum__*` / `Type_Safe__*` class.

### A.2 `runtime: str = 'python3.12'` — string-with-default for a fixed set

**Violates CLAUDE.md rule #3** ("No Literals — all fixed-value sets use `Enum__*` classes"). Lambda runtimes are a closed set per AWS.

**Compliant rewrite:**

```python
# aws/lambda_/enums/Enum__Lambda__Runtime.py
class Enum__Lambda__Runtime(Enum):
    PYTHON_3_12 = 'python3.12'
    PYTHON_3_11 = 'python3.11'
    # add more on demand
```

### A.3 Manifest uses string for stability + capabilities

**Brief** ([`04 §9`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md)):

```python
MANIFEST = Schema__Spec__Manifest__Entry(
    stability    = 'experimental',
    capabilities = ['subdomain-routing', 'on-demand-compute', 'tls-wildcard'],
)
```

**Violates rule #3.** Verified against `sg_compute_specs/vault_app/manifest.py`:

```python
# correct shape — these are Enums, not strings
stability    = Enum__Spec__Stability.EXPERIMENTAL,
capabilities = [Enum__Spec__Capability.VAULT_WRITES, ...],
```

**Compliant rewrite:**

```python
# sg_compute_specs/vault_publish/manifest.py
from sg_compute.primitives.enums.Enum__Spec__Stability  import Enum__Spec__Stability
from sg_compute.primitives.enums.Enum__Spec__Capability import Enum__Spec__Capability
from sg_compute.primitives.enums.Enum__Spec__Nav_Group  import Enum__Spec__Nav_Group

MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id              = 'vault_publish'                                  ,
    display_name         = 'Vault Publish'                                  ,
    icon                 = '🌐'                                              ,   # operator-facing
    version              = _read_version()                                  ,
    stability            = Enum__Spec__Stability.EXPERIMENTAL               ,
    boot_seconds_typical = 60                                               ,
    capabilities         = [...],                                              # need to add new Enum__Spec__Capability members
                                                                               # or pick from existing — see open question Q5
    nav_group            = Enum__Spec__Nav_Group.STORAGE                    ,
)
```

If "subdomain-routing", "on-demand-compute", "tls-wildcard" are not in `Enum__Spec__Capability` today, the **architect-owned action** is either to add them (one-line additions to the existing enum file, requires schema-catalogue update per CLAUDE.md rule #20) or to pick the closest existing capabilities. Flagged in `06__open-questions.md` Q5.

### A.4 `dns_swap_marker : Set__Str` (brief [`04 §5.2`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md))

The brief invents `Set__Str` as if it were a Type_Safe type. **No such class exists today.** osbot-utils provides `Type_Safe__List` and `Type_Safe__Dict` but not a `Set` collection (verified — only List and Dict subclasses are referenced in the codebase).

**Compliant rewrite:**

```python
# replace Set__Str with a typed dict — values are markers, keys are slugs
dns_swap_marker : Type_Safe__Dict__Safe_Str__Slug__Bool      # slug → True once swapped
```

…or `Type_Safe__List__Safe_Str__Slug` with `in` check (cheaper to model; slightly slower at scale, fine for the Lambda-instance lifetime). Architect's preference: dict, for O(1) lookup.

### A.5 `Optional[Schema__Vault_Publish__Entry]` (brief [`04 §2`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md))

```python
def get(self, slug: str) -> Optional[Schema__Vault_Publish__Entry]: ...
```

The codebase convention (verified — every `*__Service.get_*` method on `Vault_App__Service.py`) returns the schema directly or `None`. `Optional` is acceptable Python typing, but the **return-empty-schema-with-error** pattern is preferred by the project where the absence is a normal case (see how `Vault_App__Auto_DNS` returns a `Schema__Vault_App__Auto_DNS__Result` with `error` populated rather than raising). Architect's preference for `Slug__Registry.get`: keep `Optional` (this is a true "absent" case, not an error), but ensure the type alias matches the rest of the codebase (`Optional[Schema__Vault_Publish__Entry] = None` not `Schema__Vault_Publish__Entry | None`).

### A.6 `slug: str` everywhere in the orchestrator method signatures

```python
def register(self, slug: str, vault_key: str, owner: str = '', region: str = '') -> ...
```

**Borderline.** Strictly, `Type_Safe` method *arguments* are allowed to be raw `str` (the no-raw-primitive rule applies to *attributes*, not arguments). However, the codebase prefers `@type_safe`-decorated methods with `Safe_Str__*` parameters when the string carries domain meaning — see `Route53__AWS__Client` methods that take `Safe_Str__Domain_Name`.

**Compliant rewrite:**

```python
from osbot_utils.type_safe.type_safe_core.decorators.type_safe import type_safe

@type_safe
def register(self, slug         : Safe_Str__Slug              ,
                   vault_key    : Safe_Str__Vault__Key        ,
                   owner        : Safe_Str__Caller_Id   = ''  ,
                   region       : Safe_Str__AWS__Region = ''  ,
             ) -> Schema__Vault_Publish__Register__Response:
    ...
```

The CLI surface (`Cli__Vault_Publish.py`) stays loose (`typer.Option(...)` parameters are raw strings — that's the Typer contract), but the orchestrator method gets the typed signature.

### A.7 Slug validation timing

The brief's `register` shows `validate slug → return error if invalid`. Combined with A.6, **the `Safe_Str__Slug` constructor itself enforces charset and length**. The `Slug__Validator` adds reserved-word + double-hyphen / leading-hyphen / profanity policy on top. That means:

1. Calling code constructs `Safe_Str__Slug('sara-cv')` — fails fast if charset / length wrong (raises at construction).
2. `register` then calls `self.validator.validate(slug)` which returns `Enum__Slug__Error_Code.OK` or a specific reason for the policy-layer checks.

This split keeps the type-safety guarantee narrow (it just enforces the regex) and lets the policy live in one place. Compliant with rule #1 / #2 / #3.

### A.8 `Endpoint__Resolver.resolve` returns a tuple

```python
def resolve(self, entry) -> tuple:
    # returns (state, endpoint_url)
```

**Anti-pattern.** Tuples as return types are forbidden everywhere else in the codebase — every service method returns a `Schema__*`. Verified — `Vault_App__Service.create_stack` returns `Schema__Vault_App__Create__Response`, even when only one field would suffice.

**Compliant rewrite:**

```python
# waker/schemas/Schema__Endpoint__Resolution.py
class Schema__Endpoint__Resolution(Type_Safe):
    state         : Enum__Instance__State
    endpoint_url  : Safe_Str__URL   = Safe_Str__URL('')

# waker/Endpoint__Resolver.py
class Endpoint__Resolver(Type_Safe):
    def resolve(self, entry: Schema__Vault_Publish__Entry) -> Schema__Endpoint__Resolution:
        raise NotImplementedError
```

### A.9 `_delete_per_slug_a_record` (underscore-prefixed private)

**Violates CLAUDE.md rule #9** ("No underscore prefix for private methods").

**Compliant rewrite:** rename to `delete_per_slug_a_record` — public method. If there's a reason to mark it "internal", do so in the inline comment, not in the name.

### A.10 `lambda_entry.py` "AWS Lambda Web Adapter" pattern

The brief sketches `app = FastAPI()` directly at module level. Looking at the existing repo's Lambda pattern (`lambda_handler.py` precedent referenced in `.claude/CLAUDE.md` under "Architecture"), the convention is:

- A separate `lambda_handler.py` file that fires up everything on import.
- A pure class (`Fast_API__Playwright__Service`) that is importable without side effects.

**Compliant rewrite:**

```python
# waker/Fast_API__Waker.py  — pure class, no side effects on import
class Fast_API__Waker(Type_Safe):
    handler : Waker__Handler

    def setup(self) -> 'Fast_API__Waker':
        self.handler = Waker__Handler().setup()
        return self

    def app(self) -> FastAPI:
        a = FastAPI()
        @a.api_route('/{full_path:path}', methods=['GET','POST','PUT','DELETE','PATCH'])
        async def catchall(request: Request, full_path: str):
            return await self.handler.handle(request)
        return a

# waker/lambda_entry.py  — entry point, fires up on import
from sg_compute_specs.vault_publish.waker.Fast_API__Waker import Fast_API__Waker
app = Fast_API__Waker().setup().app()
```

This mirrors the established pattern and keeps the spec-style import boundary intact.

### A.11 `Vault_Publish__Service` field names with multiple AWS clients

The brief shows:

```python
class Vault_Publish__Service(Spec__Service__Base):
    cf_client       : CloudFront__AWS__Client
    lambda_client   : Lambda__AWS__Client
    lambda_deployer : Lambda__Deployer
```

These are fine, but `cf_client` / `lambda_client` should match the project's existing field-naming convention. `Vault_App__Service` uses `aws_client : Optional[Vault_App__AWS__Client] = None` — single field, single client. Where multiple are needed (rare), the convention from `Spec__Service__Base` and existing services suggests fully-qualified names. Suggested:

```python
class Vault_Publish__Service(Spec__Service__Base):
    validator       : Optional[Slug__Validator]         = None
    registry        : Optional[Slug__Registry]          = None
    vault_app       : Optional[Vault_App__Service]      = None
    route53_client  : Optional[Route53__AWS__Client]    = None
    cf_client       : Optional[CloudFront__AWS__Client] = None
    lambda_deployer : Optional[Lambda__Deployer]        = None

    def setup(self) -> 'Vault_Publish__Service':
        self.validator       = Slug__Validator      ().setup()
        ...
```

(The `Optional[...] = None` + `setup()` pattern is verified at `Vault_App__Service.py:50-64`.)

### A.12 `OPTIONAL` shape rather than required for `--cert-arn`

Brief `bootstrap` flow ([`04 §6`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) step 2): "If `--cert-arn` was passed, use that. If not and not found, print instructions for manual issuance." This is right; **make sure** `Schema__Vault_Publish__Bootstrap__Request.cert_arn : Safe_Str__ACM__ARN = Safe_Str__ACM__ARN('')` defaults to empty (the `allow_empty=True` flag on the Safe_Str primitive, per pattern in `Vault_App__Service` fields).

### A.13 Brief's `Endpoint__Resolver__Fargate` listed under [`04 §1`](file:///tmp/vault-publish-brief/04__vault-publish-spec.md) folder layout

The folder layout file-tree shows `Endpoint__Resolver__Fargate.py` as if it lands in phase 2. **Brief contradicts itself** — text marks it as phase 3 ("PROPOSED — does not exist yet" per the brief itself). Action: do NOT create this file in the v2 phase 2 work. Add a comment in `Endpoint__Resolver.py` noting the Fargate subclass is phase 3.

---

## B. Lab-brief deltas (parallel sibling track, not in vault-publish critical path)

The lab-brief is a **measurement harness** for the same primitives the v2 brief builds. It is excellent work, but it is not a dependency of vault-publish v2. The plan keeps it as a **parallel track**: it can land before, alongside, or after the v2 implementation without affecting the v2 deliverable.

That said, several of the lab-brief's design choices would violate project rules if Dev picked them up unchanged. The corrections below apply only when Dev tackles the lab brief separately.

### B.1 `Set__Str` (lab-brief 05 §3, `dns_swap_marker`)

Same as A.4 above. No `Set__Str` exists. Use `Type_Safe__Dict__*` or `Type_Safe__List__*`.

### B.2 `Lab__Experiment.execute(self, runner: 'Lab__Runner')`

Forward-reference string for the runner. Acceptable Python, but **the codebase prefers `setup() → 'Self'`-style fluent composition** over passing collaborator objects into per-method calls. Compliant rewrite: inject the runner at `setup` time as a field, not at call time as an argument.

```python
class Lab__Experiment(Type_Safe):
    runner : Optional['Lab__Runner'] = None

    def setup(self, runner: 'Lab__Runner') -> 'Lab__Experiment':
        self.runner = runner
        return self

    def execute(self) -> Schema__Lab__Run__Result:
        raise NotImplementedError
```

### B.3 Experiment filenames `E01__zone_inventory.py` (lab-brief 05 §1)

The leading `E01__` numeric prefix is a documentation convention (it sorts the directory listing), but it produces module names that violate Python's PEP 8 implicit "modules should be short, lowercase, with underscores". More importantly, **CLAUDE.md rule #21 says "one class per file, file named exactly after the class"**. So the file should be:

```
Lab__Experiment__Zone_Inventory.py     # contains class Lab__Experiment__Zone_Inventory
```

The `E01` mapping lives in a registry (`registry.py`) or in the class metadata, not the filename. This is consistent with the rest of the codebase.

### B.4 `Dict__Str__Str` / `Dict__Str__Int` (lab-brief 05 §2)

These are sketched as if they're real types. The codebase uses `Type_Safe__Dict` with class generics; the equivalent today is to subclass — e.g. `Type_Safe__Dict__Safe_Str__Safe_Str` per CLAUDE.md rule #21 (one class per file, in `collections/`).

### B.5 The `temp_clients/` directory — boto3 wrappers slated for deletion

The lab-brief's plan to create `Lab__CloudFront__Client__Temp` and `Lab__Lambda__Client__Temp`, then delete them when `sg aws cf` / `sg aws lambda` land, is sound — but it means **the lab cannot ship its CF/Lambda experiments before vault-publish phase 2a/2b without introducing throwaway boto3 wrappers**. The plan's recommendation: skip the temp-client work entirely. Land lab P0+P1 (DNS only — no temp client needed) first, then wait for vault-publish phase 2a/2b to ship `sg aws cf` and `sg aws lambda`, then resume lab P2+P3. This avoids the "delete the temp client" merge dance and saves Dev cycles.

### B.6 The lab-brief mounts `sg aws lab` — fine, but be careful about timing

If the lab harness lands first (before `sg aws cf`/`sg aws lambda`), `Cli__Aws.py` gains a sibling Typer (`lab`) before its full set of CF/Lambda siblings exists. Not a violation — just a sequencing note. Mount order: `dns`, `acm`, `lab`, (later) `cf`, `lambda`.

### B.7 Lab-brief safety story is OUT OF SCOPE of vault-publish v2

The three-layer ledger + atexit + signal handler + sweeper is excellent for the lab. **The vault-publish spec does not need this machinery** — its mutations are operator-initiated `register` / `unpublish`, not throwaway experimental resources. Dev should **not** generalise the ledger pattern into the vault-publish spec.

The lab brief's safety story is the lab brief's deliverable. The vault-publish spec follows the existing mutation-gating convention (`SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1`) and that's enough.

---

## C. Summary — what Dev should NOT do

Three things from the brief / lab-brief Dev should explicitly skip:

1. **Do not copy schema sketches verbatim from the brief.** Apply A.1 / A.2 / A.3 / A.4 / A.8 every time.
2. **Do not adopt the lab-brief's experiment-file naming (`E01__...`)** — use the class-name convention (B.3).
3. **Do not generalise the lab-brief's ledger/atexit pattern into vault-publish** — it does not belong there (B.7).
