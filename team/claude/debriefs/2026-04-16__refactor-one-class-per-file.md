# Debrief — One-class-per-file refactor

- **Date:** 2026-04-16
- **Observation driving this:** `team/claude/observations/2026-04-16__one-class-per-file.md` (from Dinis's `@dev` comment in the old `vault.py`).

## What was delivered

Each of the following modules was split into a same-named folder containing one class per file:

### Primitives (`schemas/primitives/`)
- `vault.py` → `vault/Safe_Str__Vault_Key.py`, `vault/Safe_Str__Vault_Path.py`
- `s3.py` → `s3/Safe_Str__S3_Key.py`, `s3/Safe_Str__S3_Bucket.py`
- `browser.py` → `browser/Safe_Str__Selector.py`, `browser/Safe_Str__Browser__Launch_Arg.py`, `browser/Safe_Str__JS__Expression.py`
- `numeric.py` → 5 `Safe_UInt__*.py` files
- `host.py` → `host/Safe_Str__Host.py`
- `identifiers.py` → 4 files (done earlier in the session)

### Enums (`schemas/enums/`)
- `enums.py` → 16 `Enum__*.py` files

### Schemas
- `service/service.py` → `service/Schema__Service__Capabilities.py`, `Schema__Service__Info.py`, `Schema__Health__Check.py`, `Schema__Health.py`
- `browser/browser.py` → `browser/Schema__Proxy__Config.py`, `Schema__Viewport.py`, `Schema__Browser__Config.py`
- `artefact/artefact.py` → `artefact/Schema__Vault_Ref.py`, `Schema__S3_Ref.py`, `Schema__Local_File_Ref.py`, `Schema__Artefact__Sink_Config.py`, `Schema__Artefact__Ref.py`
- `capture/capture.py` → `capture/Schema__Capture__Config.py`

Every `__init__.py` stays empty. Every caller imports from the fully-qualified per-class path.

### Import sites updated
- 5 primitive test files (`test_vault.py`, `test_s3.py`, `test_browser.py`, `test_numeric.py`, `test_identifiers.py`)
- `test_enums.py`
- All cross-schema imports inside the split files (e.g. `Schema__Browser__Config` → `Schema__Proxy__Config`, `Schema__Viewport`)

## Verification

- 70 unit tests pass locally.
- All four split schemas import cleanly and `Schema__Capture__Config().json()` produces the expected default payload.

## Issues / bugs hit

- **Coexistence trap:** I had previously committed the new per-class folders (with empty `__init__.py`) alongside the old consolidated modules. Python's import system prefers a package over a module of the same name, so the tests collapsed with `ImportError: cannot import name 'Safe_Str__Vault_Key' from '...schemas.primitives.vault'` — it was finding the empty package, not the module. Fix: finish the split and delete the old modules in the same commit.
- Nothing subtle otherwise — mechanical work.

## Lessons

- Never commit an empty package alongside a same-named module. It shadows the module and every import under it breaks at collection time. Either finish the split in one go or defer creating the package folder.
- Verify imports immediately after the first split in a series; don't wait until you've split five modules to learn one of them is mis-imported.

## Follow-up (not done here)

- Add a rule to `.claude/CLAUDE.md` Code Patterns: "One class per file. Consolidated modules are forbidden." (See `observations/2026-04-16__one-class-per-file.md` for the proposed text.)
- Still pending: Phase 1.3 §5.5–§5.10, §6 collections, §8 step registries, plus unit tests for the service/browser/artefact/capture schemas.
