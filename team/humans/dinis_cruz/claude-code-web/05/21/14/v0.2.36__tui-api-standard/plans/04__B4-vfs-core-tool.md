---
title: "B4 — the VFS core tool (memory_fs + /tools/<tool>/ conventions)"
file: 04__B4-vfs-core-tool.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — pure logic; provider tests gated on Python 3.12 (memory_fs).
parent: 00__plans-index.md
---

# B4 — the VFS core tool

**Goal.** Ship the first **core tool**: a `Tui_Api__Provider` over a `memory_fs` `Storage_FS`,
exposing CRUD on files/folders as tiered actions, plus the **standard `/tools/<tool>/` doc
tree** that tools populate so an agent reads orientation/skills/changelog **on demand** —
files-as-tool, not context (standard §6). Disabled by default; granted per workflow.

---

## What exists (verified)

`memory_fs` (PyPI, **Python 3.12**) — `Storage_FS` interface with backends
`Storage_FS__Memory` (default), `Storage_FS__Local_Disk`, `Storage_FS__Sqlite`, `Storage_FS__Zip`.
CRUD verified this session: `file__save(path, bytes)`, `file__str/bytes/json/exists/delete`,
`files__paths()`, `folder__folders(parent, return_full_path=False)`, `folder__files__all(parent)`,
`clear()`. `Memory_FS__In_Memory` = `Memory_FS` + `Storage_FS__Memory`.

---

## Files to create

```
tui/tool_api/core/vfs/
  schemas/
    Schema__Vfs__Params__Path.py        path: Safe_Str__File__Path
    Schema__Vfs__Params__Write.py       path: Safe_Str__File__Path · content: str
    Schema__Vfs__Params__Move.py        src: Safe_Str__File__Path · dst: Safe_Str__File__Path
  Vfs__Tui_Api__Provider.py             wraps a Storage_FS; manifest + dispatch
  Vfs__Doc_Tree.py                      writes/reads the /tools/<tool>/ convention tree
  bedrock_chat_vfs__config.py           default backend + the conventional file names
  tests/
    test_Vfs__Tui_Api__Provider.py      (3.12-gated; uses Storage_FS__Memory)
    test_Vfs__Doc_Tree.py               (3.12-gated)
```

`memory_fs` is a new dependency, declared in the **TUI extra** (not the Lambda/Fargate
runtime) and pinned for 3.12; the contract/registry/exec-center (B1–B3) stay import-clean of it.

---

## Actions (the VFS as a TUI API)

| action | tier | params | maps to |
|---|---|---|---|
| `vfs.list` | READ_ONLY | path | `folder__files__all(path)` |
| `vfs.tree` | READ_ONLY | path | `folder__folders(path)` + files, recursive render |
| `vfs.read` | READ_ONLY | path | `file__str(path)` (or `file__bytes`) |
| `vfs.stat` | READ_ONLY | path | `file__exists` + size |
| `vfs.write` | WRITE | path, content | `file__save(path, content.encode())` |
| `vfs.mkdir` | WRITE | path | save a `.keep` (memory_fs is file-keyed; folders are path prefixes) |
| `vfs.move` | WRITE | src, dst | read+save+delete |
| `vfs.delete` | DESTRUCTIVE | path | `file__delete(path)` |
| `vfs.clear` | DESTRUCTIVE | (none) | `clear()` |

```python
class Vfs__Tui_Api__Provider(Tui_Api__Provider):
    storage : 'Storage_FS'                       # Storage_FS__Memory by default; swap to persist (#6)
    def manifest(self): ...                      # the actions above, with input_schema from the params classes
    def state(self):    return {'files': self.storage.files__paths()}   # outbound 'state' surface
    def dispatch(self, action, params):
        # thin mapping onto the Storage_FS methods; WRITE+/DESTRUCTIVE gated by B3, not here
        ...
```

WRITE/DESTRUCTIVE tiers mean the **execution center** (B3) gates them (confirm / dry-run /
`..._ALLOW_MUTATIONS`); the provider itself is a thin, honest mapping with no gating logic.

---

## The doc-tree convention (standard §6)

`Vfs__Doc_Tree` writes/reads the opinionated tree a tool self-populates at startup so an agent
can orient without context pollution:

```
/tools/<tool>/
  skills.md  changelog.md  whatsnew.md  coming-soon.md  known-issues.md
  current-state.json   workflows/<name>.md   api/<api-slug>.json
```

```python
class Vfs__Doc_Tree(Type_Safe):
    storage : 'Storage_FS'
    tool    : str
    def root(self)          -> str   # f'/tools/{self.tool}/'
    def put_skills(self, md: str)            : self.storage.file__save(self.root()+'skills.md', md.encode())
    def put_manifest(self, slug, manifest_dict): ...   # api/<slug>.json
    def put_state(self, state_dict)          : ...     # current-state.json
    def read(self, rel_path)-> str           : return self.storage.file__str(self.root()+rel_path)
```

A provider's `populate_vfs(vfs)` (the seam from the standard) calls `Vfs__Doc_Tree` to drop
its `skills.md` + `api/<slug>.json` + `current-state.json`. Change-control files
(`changelog.md`/`whatsnew.md`) are **recommended, not required** (decision #5) — a minimal tool
can ship just `skills.md`.

---

## Tests (no mocks; 3.12 via /tmp/venv312)

- `test_Vfs__Tui_Api__Provider` — build with `Storage_FS__Memory`; `vfs.write` then `vfs.read`
  round-trips; `vfs.list`/`vfs.tree` reflect the tree; `vfs.delete` removes; `vfs.stat` reports
  existence/size; unknown action → `ok==False`. (Ephemeral: a fresh provider starts empty — #6.)
- `test_Vfs__Doc_Tree` — `put_skills` + `put_manifest` then `read('skills.md')` and
  `read('api/sg-aws.s3.json')` return what was written; `root()` == `/tools/<tool>/`.
- Gating header: `@skipUnless(memory_fs importable)` so the suite skips cleanly on 3.11; the 3.12
  venv runs it. (Mirror the Textual gating pattern already used by the chat pilot tests.)

---

## Acceptance (B4 done-when)

1. The VFS provider exposes `vfs.*` as tiered actions discoverable via `sg … tui api describe`.
2. CRUD round-trips on `Storage_FS__Memory`; ephemeral by default (lost on close — #6).
3. WRITE/DESTRUCTIVE `vfs.*` are gated by the B3 execution center (verified via a pilot/unit that a delete needs confirm/ALLOW_MUTATIONS).
4. `Vfs__Doc_Tree` writes/reads the standard `/tools/<tool>/` tree; a provider can `populate_vfs`.
5. `memory_fs` is isolated to the TUI extra; B1–B3 stay import-clean of it; tests gated on 3.12.

## Effort / risk

- **Effort:** ~1 day. The store exists and is verified; B4 is the thin provider + doc-tree + gated tests.
- **Risk — memory_fs folder semantics.** It is file-keyed (folders are path prefixes); `vfs.mkdir`
  writes a `.keep`. Document this; `vfs.tree` derives folders from `folder__folders`.
- **Risk — 3.12 gating in CI.** Coordinate with DevOps that the TUI extra + 3.12 lane runs the gated
  suite; on the 3.11 default lane these tests skip (don't fail).
- **Open (defer):** seeding a session's VFS from disk (`--vfs-seed <dir>`) — the standard's seeding
  open-Q; not in B4. Persistence to local/sqlite/zip is a one-line backend swap when wanted.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
