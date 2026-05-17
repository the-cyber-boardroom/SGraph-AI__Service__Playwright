# CLI Surface

**Domain:** `sg-compute/` | **Subarea:** `sg_compute/cli/` + `sgraph_ai_service_playwright__cli/aws/*` | **Last updated:** 2026-05-17

The `Spec__CLI__Builder` factory (v0.2.6), the `sg aws billing` sub-package (v0.2.22), and the `sg vp` vault-publish CLI (v0.2.23) — plus the supporting `sg aws cf` and `sg aws lambda` primitives that the vault-publish CLI depends on.

---

## EXISTS

### sg_compute/cli/base/ — v0.2.6

| Class | Path | Description |
|-------|------|-------------|
| `Spec__CLI__Builder` | `cli/base/Spec__CLI__Builder.py` | Factory; produces a `typer.Typer` with all 8 standard verbs from a `Schema__Spec__CLI__Spec`. Plain class (not Type_Safe). |
| `Spec__CLI__Resolver` | `cli/base/Spec__CLI__Resolver.py` | Auto-pick / prompt / error rule for optional `name`. |
| `Spec__CLI__Errors` | `cli/base/Spec__CLI__Errors.py` | `@spec_cli_errors` decorator + `set_debug()`. Module-level `_DEBUG` flag. |
| `Spec__CLI__Defaults` | `cli/base/Spec__CLI__Defaults.py` | `DEFAULT_REGION`, `DEFAULT_MAX_HOURS=1`, `DEFAULT_TIMEOUT_SEC=600`, `DEFAULT_POLL_SEC=10`, `DEFAULT_EXEC_TIMEOUT=60`. |
| `Schema__Spec__CLI__Spec` | `cli/base/Schema__Spec__CLI__Spec.py` | Per-spec configuration consumed by the builder. Plain class (holds class refs + callables). |
| `Spec__CLI__Renderers__Base` | `cli/base/Spec__CLI__Renderers__Base.py` | Default Rich renderers: `render_list`, `render_info`, `render_create`, `render_delete`, `render_health_probe`, `render_exec_result`. |
| `Schema__CLI__Exec__Result` | `cli/base/schemas/Schema__CLI__Exec__Result.py` | `stdout/stderr: str`, `exit_code: Safe_Int__Exit__Code`, `transport: str`, `duration_ms: int`, `error: str`. |
| `Schema__CLI__Health__Probe` | `cli/base/schemas/Schema__CLI__Health__Probe.py` | `healthy: bool`, `state: str`, `elapsed_ms: int`, `last_error: str`. |

Contract doc: `library/docs/specs/v0.2.6__spec-cli-contract.md`.

### sgraph_ai_service_playwright__cli/aws/billing/ — EXISTS (v0.2.22)

Six `sg aws billing` commands backed by AWS Cost Explorer.

#### Primitives

| Class | Path | Notes |
|-------|------|-------|
| `Safe_Decimal__Currency__USD` | `billing/primitives/Safe_Decimal__Currency__USD.py` | Decimal-backed USD; `decimal_places=4`; `min_value=None` (credits are legitimately negative); extends `Safe_Float__Money` |
| `Safe_Str__Aws_Service_Code` | `billing/primitives/Safe_Str__Aws_Service_Code.py` | CE service display name; permissive regex `r'[^A-Za-z0-9 \-().,/&_]'`; `allow_empty=True` |
| `Safe_Str__Iso8601_Date` | `billing/primitives/Safe_Str__Iso8601_Date.py` | YYYY-MM-DD date string |
| `Safe_Str__Aws_Usage_Type` | `billing/primitives/Safe_Str__Aws_Usage_Type.py` | CE usage type string |

#### Enums

| Class | Values |
|-------|--------|
| `Enum__Billing__Granularity` | `DAILY / HOURLY / MONTHLY` |
| `Enum__Billing__Metric` | `UNBLENDED_COST / BLENDED_COST / NET_UNBLENDED_COST / AMORTIZED_COST` |
| `Enum__Billing__Group_By` | `SERVICE / USAGE_TYPE / LINKED_ACCOUNT / REGION` |
| `Enum__Billing__Window_Keyword` | `LAST_48H / LAST_7D / MONTH_TO_DATE` |

#### Schemas (pure data, no methods)

| Class | Key fields |
|-------|------------|
| `Schema__Billing__Window` | `start / end (Safe_Str__Iso8601_Date)`, `granularity (Enum)`, `keyword (str)` |
| `Schema__Billing__Line_Item` | `service (Safe_Str__Aws_Service_Code)`, `amount_usd (Safe_Decimal__Currency__USD)`, `metric (Enum)` |
| `Schema__Billing__Daily_Bucket` | `date`, `total_usd`, `line_items (List__Schema__Billing__Line_Item)` |
| `Schema__Billing__Report` | `window`, `metric`, `group_by`, `buckets`, `total_usd`, `account_id`, `currency='USD'`, `generated_at` |

#### Collections

`List__Schema__Billing__Daily_Bucket`, `List__Schema__Billing__Line_Item`, `List__Schema__Billing__Group` (scaffolded, unused in MVP).

#### Service layer

| Class | Path | Notes |
|-------|------|-------|
| `Cost_Explorer__AWS__Client` | `billing/service/Cost_Explorer__AWS__Client.py` | Sole boto3 boundary for CE + STS. `client()` is the test seam. Manual `NextPageToken` pagination. `RECORD_TYPE=Usage` filter by default; empty list = all charges. Splits `DataUnavailableException` (CE disabled) from `AccessDeniedException` (IAM missing). Validates all amounts are USD. |
| `Billing__Window__Resolver` | `billing/service/Billing__Window__Resolver.py` | Maps `'last-48h'` / `'week'` / `'mtd'` keywords → `(start, end, granularity)` tuples |
| `Billing__Report__Builder` | `billing/service/Billing__Report__Builder.py` | `ce_client=None` (lazy-inits in `setup()`); `build(start, end, granularity, keyword, metric, group_by_key, top_n, all_charges)` → `Schema__Billing__Report` |

#### CLI commands

Registered as `billing_app` in `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py`.

| Command | Description |
|---------|-------------|
| `sg aws billing last-48h` | Daily breakdown, last 2 days |
| `sg aws billing week` | Daily breakdown, last 7 days |
| `sg aws billing mtd` | Month-to-date daily breakdown |
| `sg aws billing window --start YYYY-MM-DD --end YYYY-MM-DD` | Custom date range |
| `sg aws billing summary` | Aggregated service totals: share % + horizontal bars |
| `sg aws billing chart` | Daily totals bar chart: ▲ peak / ▼ low markers, stats footer |

All commands accept `--all-charges` to include credits/refunds/taxes.

#### IAM requirements

`ce:GetCostAndUsage` + `sts:GetCallerIdentity` on `Resource: "*"` (mandatory — CE has no resource-level IAM). `ce:GetDimensionValues` optional.

### Vault-publish CLI (cli/) — v0.2.23

| Command | Description |
|---------|-------------|
| `sg vp register <slug> --vault-key <key>` | Create vault-app stack + register slug in SSM |
| `sg vp unpublish <slug>` | Delete stack + remove slug from SSM |
| `sg vp status <slug>` | Show EC2 state + FQDN |
| `sg vp list` | List all registered slugs (vault keys redacted) |
| `sg vp bootstrap [--cert-arn ARN] [--zone ZONE] [--role-arn ARN]` | Deploy Waker Lambda + create Lambda Function URL + create CF distribution |

Mutation guard: `SG_AWS__CF__ALLOW_MUTATIONS=1` required for bootstrap CF creation.

### sgraph_ai_service_playwright__cli/aws/cf/ — EXISTS (v0.2.23)

CloudFront CRUD primitive. Sole boto3 boundary for CF. Guarded by `SG_AWS__CF__ALLOW_MUTATIONS=1`.

| Layer | Classes |
|-------|---------|
| Enums | `Enum__CF__Distribution__Status` (Deployed/InProgress), `Enum__CF__Price__Class`, `Enum__CF__Origin__Protocol` |
| Primitives | `Safe_Str__CF__Distribution_Id`, `Safe_Str__CF__Domain_Name`, `Safe_Str__Cert__Arn`, `Safe_Str__CF__Origin_Id` |
| Collections | `List__CF__Alias`, `List__Schema__CF__Distribution`, `List__Schema__CF__Origin` |
| Schemas | `Schema__CF__Distribution`, `Schema__CF__Create__Request`, `Schema__CF__Create__Response`, `Schema__CF__Action__Response`, `Schema__CF__Origin` |
| Service | `CloudFront__Distribution__Builder` (builds DistributionConfig dict), `CloudFront__Origin__Failover__Builder`, `CloudFront__AWS__Client` (list/get/create/disable/delete/wait_deployed) |
| CLI | `Cli__Cf.py` — `sg aws cf distributions list/show/create/disable/delete/wait` |

Test helper: `tests/unit/.../CloudFront__AWS__Client__In_Memory.py` — dict-backed fake, monotonic counter for IDs, `set_deployed()` shortcut. 36 tests.

### sgraph_ai_service_playwright__cli/aws/lambda_/ — EXISTS (v0.2.23)

Lambda deploy + URL CRUD primitive.

| Layer | Classes |
|-------|---------|
| Enums | `Enum__Lambda__Url__Auth_Type` (NONE/AWS_IAM), `Enum__Lambda__Runtime` (Python 3.11/3.12/3.13), `Enum__Lambda__State` (ACTIVE/INACTIVE/PENDING/FAILED) |
| Primitives | `Safe_Str__Lambda__Name`, `Safe_Str__Lambda__Arn`, `Safe_Str__Lambda__Url` |
| Collections | `List__Schema__Lambda__Function` |
| Schemas | `Schema__Lambda__Function`, `Schema__Lambda__Deploy__Request`, `Schema__Lambda__Deploy__Response`, `Schema__Lambda__Url__Info`, `Schema__Lambda__Action__Response` |
| Service | `Lambda__AWS__Client` (list/get/exists/get_function_url/create_function_url/delete_function_url/delete_function), `Lambda__Deployer` (zip-and-deploy from folder, create or update) |
| CLI | `Cli__Lambda.py` — `sg aws lambda deploy/list/delete` + `url create/show/delete` |

Test helpers: `tests/unit/.../Lambda__AWS__Client__In_Memory.py` + `Lambda__Deployer__In_Memory`. 16 tests.

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`specs.md`](specs.md) — the `vault_publish` spec, slug registry, Waker Lambda (what `sg vp` drives)
- [`primitives.md`](primitives.md) — `Safe_Int__Exit__Code` and other primitives consumed by the builder
- [`pods.md`](pods.md) — `Routes__Compute__*` HTTP surface (the CLI's server-side counterpart)
