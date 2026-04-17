# Observation — One class per file for primitives / enums / schemas

- **Date captured:** 2026-04-16
- **Source:** Dinis Cruz — commit `05e4173` (`added comment to @dev agent`), inline in `sgraph_ai_service_playwright/schemas/primitives/vault.py` lines 15–17
- **Status:** COMPLETED. Refactor landed — see `debriefs/2026-04-16__refactor-one-class-per-file.md`. The old `vault.py` (along with the `@dev` comment it carried) was deleted as part of the split. `.claude/CLAUDE.md` still to be updated with the "one class per file" rule.

## Original comment (verbatim)

```python
# @dev can you refactor each of these classes into its own file
#      you can put them in a folder with the same name as the current file
#      in this case /schemas/primitives/vault/Safe_Str__Vault_Key.py
```

## Interpretation

For every currently-consolidated module that declares more than one `Safe_*` / `Enum__*` / `Schema__*` class:

1. Create a subfolder with the same stem as the consolidated file (e.g. `vault.py` → `vault/`).
2. Move each class into its own file named exactly after the class (e.g. `vault/Safe_Str__Vault_Key.py`, `vault/Safe_Str__Vault_Path.py`).
3. Keep `__init__.py` empty (see `2026-04-16__empty-init-files.md`).
4. Callers import from the class-named sub-file: `from sgraph_ai_service_playwright.schemas.primitives.vault.Safe_Str__Vault_Key import Safe_Str__Vault_Key`.
5. Delete the old consolidated `.py` file.

## Scope

- `schemas/primitives/vault.py` → `vault/Safe_Str__Vault_Key.py`, `vault/Safe_Str__Vault_Path.py`
- `schemas/primitives/s3.py` → `s3/Safe_Str__S3_Key.py`, `s3/Safe_Str__S3_Bucket.py`
- `schemas/primitives/browser.py` → `browser/Safe_Str__Selector.py`, `browser/Safe_Str__Browser__Launch_Arg.py`, `browser/Safe_Str__JS__Expression.py`
- `schemas/primitives/numeric.py` → 5 sub-files
- `schemas/primitives/identifiers.py` → `identifiers/Session_Id.py`, `identifiers/Sequence_Id.py`, `identifiers/Step_Id.py`, `identifiers/Safe_Str__Trace_Id.py` **(done)**
- `schemas/primitives/vault.py`, `s3.py`, `browser.py`, `numeric.py`, `host.py` → per-class files **(done)**
- `schemas/enums/enums.py` → 16 `Enum__*.py` files **(done)**
- `schemas/service/service.py`, `schemas/browser/browser.py`, `schemas/artefact/artefact.py`, `schemas/capture/capture.py` → per-class `Schema__*.py` files **(done)**
- `schemas/primitives/host.py` → `host/Safe_Str__Host.py`
- `schemas/enums/enums.py` → `enums/Enum__*.py` (16 files)
- `schemas/service/service.py`, `schemas/browser/browser.py`, `schemas/artefact/artefact.py`, `schemas/capture/capture.py` → per-class files each

## Rolled-into-guidelines

- **Update target:** `.claude/CLAUDE.md` "Class / File Naming" section. Add a new rule:

  > **One class per file.** Every `Safe_*`, `Enum__*`, and `Schema__*` class lives in its own file named exactly after the class. When a module would otherwise declare multiple classes, replace it with a same-named folder containing per-class files. Callers import from the class file directly. `__init__.py` stays empty.

- Once this rule is in CLAUDE.md, delete the `@dev` comment from `vault.py`.
