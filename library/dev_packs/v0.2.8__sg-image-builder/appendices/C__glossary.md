# Appendix C — Glossary

Quick definitions for every term used in this pack. Alphabetical.

| Term | Definition |
|---|---|
| **AL2023** | Amazon Linux 2023, the default base AMI for sgi v1 |
| **AMI** | Amazon Machine Image. sgi's purpose is to *avoid* depending on custom AMIs for fast cold-start. |
| **Bake** | The full strip workflow: load → strip → re-capture → publish at a bumped version. `sgi strip bake`. |
| **Boot** | Second of the three canonical performance moments (P17). Time from "bundle on disk" to "service ready". |
| **Bundle** | A captured slice of filesystem state, packaged as `manifest.json + payload.tar.zst + sidecar.zip`. Unit of distribution. |
| **Capture** | The act of recording filesystem state changes during an installation. Produces a `Schema__Capture__Diff`. |
| **Catalog** | `catalog.json` at the root of Storage; index of all published bundles and recipes. |
| **CBR** | Cyber-Boardroom; source of the SSH deployment pattern in `CBR__Athena__Deploy__*.py`. |
| **Cold-start** | The composite performance metric: time from `RunInstances` API call to first successful workload execution. |
| **DLAMI** | Deep Learning AMI from AWS. Used as a base for GPU specs. Includes nvidia drivers + CUDA. |
| **E2E** | End-to-end. The slowest, most realistic test layer. Real AWS, real SSH, real bundles. Gated by `SGI_E2E_ENABLED`. |
| **EBS** | Elastic Block Store. AWS's block storage. Lazy-loads from S3 by default, which is the slow cold-start cause sgi avoids. |
| **Ephemeral** | Single-use; created, used, destroyed in one operation. sgi's build instances are ephemeral. |
| **Event bus** | The internal `Events__Emitter` channel where every operation publishes structured events. Sinks include JSONL and Elasticsearch. |
| **Execution** | Third of the three canonical performance moments (P17). Time per workload operation. |
| **Exec_Provider** | The abstract interface for remote command execution. Implementations: `SSH`, `Sg_Compute`, `Twin`. |
| **First load** | First of the three canonical performance moments (P17). Time from "bundle not present" to "bundle on disk". |
| **IFD** | Iterative Flow Development versioning. Paths like `v0/v0.1/v0.1.0/` — each level is the cumulative version up to that point. Path is immutable. |
| **In_Memory** | A provider that uses dict-backed storage. For tests. Wipes on process exit. |
| **Local_Disk** | A provider that mirrors the S3 tree on a local filesystem path. For air-gap and dev. |
| **Manifest** | `Schema__Bundle__Manifest`. Structured description of what's in a bundle: files, hashes, provenance. |
| **Minimal** | The most aggressive strip mode. Removes anything not exercised by end-to-end tests, including SSH if not exercised. |
| **Operation ID** | Time-ordered ID that ties events from one workflow together. Format `op_<timestamp>_<kind>`. |
| **osbot-aws** | The boto3 boundary library. sgi never imports boto3 directly. |
| **osbot-utils** | Utilities including `Type_Safe`, `SSH`, `Time__Now`. Foundation library. |
| **Payload** | `payload.tar.zst` — the captured file contents inside a bundle, compressed with zstd. |
| **Provider** | An abstract interface with multiple concrete implementations. Examples: `Storage`, `Exec_Provider`, `Events__Sink`. |
| **Recipe** | An ordered list of bundle references + per-instance values. The unit of "what to load on an instance". |
| **Replay** | The inverse of capture: take a captured state and reproduce it on a fresh target. |
| **sg lc** | The `sg-compute local-claude` CLI commands. sgi shells out to these via `Exec_Provider__Sg_Compute`. |
| **sgit** | The user's CLI tool for managing encrypted vaults. sgi never invokes sgit (P14). |
| **Sidecar** | `sidecar.zip` — per-bundle metadata: `SKILL.md`, `USAGE.md`, `SECURITY.md`, `tests/`, `performance/`. |
| **SKILL.md** | Agent-readable description of a bundle: inputs, outputs, capabilities, failure modes. Required in sidecar. |
| **Spec** | A named use case (e.g. `ssh_file_server`, `vllm_disk`). Owns a recipe template, test suite, KPIs. Specs are Python packages under `sg_image_builder_specs/`. |
| **Spot** | AWS spot pricing — lower cost, can be reclaimed. Used for ephemeral build instances. |
| **SSH provider** | `Exec_Provider__SSH`. The default. Synchronous, fast, cloud-agnostic. |
| **SSM** | AWS Systems Manager. Alternative to SSH. NOT used in sgi v1 — see P10 rationale. |
| **Storage** | The abstract interface for blob storage. Implementations: `S3`, `Local_Disk`, `In_Memory`. |
| **Strip** | The workflow of removing files not needed for the spec's purpose. Four modes: `none`, `debug`, `service`, `minimal`. |
| **Sub-timing** | Named sub-step inside a benchmark run. E.g. `ec2_run_instances`, `bundle_download_runtime`. |
| **Target** | The instance a sgi command acts on. Resolved via the workspace's `current` field. |
| **Tracked instance** | An instance added to the workspace's `state.json` tracked list. |
| **Transparency** | P2. The instance consuming a bundle cannot tell whether files arrived via real install or bundle replay. |
| **Twin** | The recording in-memory implementation of a provider. Used in tests. Lifted from `SG_Send__Deploy`'s `SSH__Execute__Twin`. |
| **Type_Safe** | The base class for all data classes. From `osbot_utils`. Strict typing, free JSON round-tripping, no Pydantic. |
| **Type__Twin** | The "alive" Type_Safe class — has both config + state + an `execute()` method. From `SG_Send__Deploy`. |
| **URI** | Bundle / recipe / object identifier with a scheme prefix: `s3://`, `file://`, `mem://`. |
| **USAGE.md** | Human-readable description of how to use a bundle correctly. Required in sidecar. |
| **Vault** | An sgit-managed folder. Encrypted, versioned, syncable. sgi treats vaults as transparent (P14). |
| **vLLM** | The LLM serving framework used for GPU specs. |
| **Workspace** | A folder containing `state.json` plus subdirs. The unit of context for sgi commands (P12). |
| **zipapp** | Python's single-file executable archive format. The v1 distribution target (P20). |
| **zstd** | The compression algorithm used for `payload.tar.zst`. Level 19. |
