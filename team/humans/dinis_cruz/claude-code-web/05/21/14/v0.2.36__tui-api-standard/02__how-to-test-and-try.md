---
title: "TUI API + Bedrock chat — how to test and try it"
file: 02__how-to-test-and-try.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 17)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: GUIDE — hands-on. Everything here is built on this branch and tested.
parent: 01__tui-api-contract-and-conventions.md
---

# How to test and try the TUI API + the tool-enabled chat

A practical walkthrough of everything built on `claude/review-tui-cli-commits-S3xCM`:
the **TUI API** (`sg <area> tui api …` + the explorer), the **VFS core tool**, and the
**Bedrock chat** that consumes them (agentic tool loop, loadout, documents, inspector).

> **Two ways to try it.** Most features have a **no-AWS path** (in-memory providers /
> scripted sources — exactly what the tests use) and a **live path** (real S3 / Bedrock,
> needs AWS creds). Start with the no-AWS path; it's reproducible anywhere.

---

## 1. What you can try

| Feature | Try it via |
|---|---|
| Discover a tool's API | `sg aws s3 tui api list / describe / skills` |
| Swagger-style explorer (Textual) | `sg aws s3 tui api explore` |
| Orientation / change-log | `sg aws s3 tui api status / whatsnew / changelog` |
| Invoke an action (gated, audited) | `sg aws s3 tui api invoke …` (needs AWS) |
| The VFS core tool | `vfs.list/read/write/…` via the chat's `--tools core.vfs:read` |
| Tool-enabled agentic chat | `sg aws bedrock chat tui --tools 'core.vfs:read'` (needs Bedrock) |
| Loadout picker · doc attach · inspector | in the chat: `ctrl+g` · `ctrl+d` · `F2` |
| Drive any provider headless | the Python snippets in §6 (no AWS) |

---

## 2. Setup

**Runtime:** the project targets **Python 3.12**. Two of the features need extra packages:

| Package | Needed for | In pyproject? |
|---|---|---|
| `textual` | the explorer + the chat TUI | ✅ yes (`*`) |
| `boto3` / `botocore` / `osbot-aws` | live AWS calls (S3 / Bedrock) | ✅ yes |
| `memory_fs` | the **VFS core tool** (Python 3.12) | ⚠️ **not yet** — install manually (see §8) |

```bash
# from the repo root, on Python 3.12
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .            # installs the package + the console scripts: sg / sgc / sp
pip install memory-fs       # for the VFS core tool (until it's added to pyproject — §8)
```

> **`sg` name clash.** The console script is `sg`, but most Linux boxes already have
> `/usr/bin/sg` (setgroup). If `sg aws …` runs the wrong thing, use the alias **`sgc`**
> (or `sp`) — same CLI. This guide writes `sg`; substitute `sgc` if needed.

**No install?** Everything is reachable from Python with the repo root on `PYTHONPATH`
(that's how the tests run — `pythonpath = ["."]` in `pyproject.toml`). See §6.

---

## 3. Run the tests

The pure layers run on **3.11**; the `memory_fs` (VFS) and agentic-pilot tests need
**3.12** and skip cleanly on 3.11.

```bash
# everything (Python 3.12 — textual + memory_fs + boto3 in one interpreter): ~113 pass
python -m pytest sgraph_ai_service_playwright__cli/tui/tool_api \
                 sgraph_ai_service_playwright__cli/aws/s3/tui_api \
                 sgraph_ai_service_playwright__cli/aws/bedrock/tui -q

# pure foundation only (no Textual needed): 
python -m pytest sgraph_ai_service_playwright__cli/tui/tool_api/tests -q

# on a 3.11 lane the VFS + agentic-screen tests SKIP (not fail) — that's expected.
```

What the suites cover (no AWS, no mocks — in-memory providers + scripted sources):
contract/registry/schema-builder, SG/Role tokens + resolver, the execution center
(sequencing/mutation-gate/audit), the VFS tool, the explorer pilot, the contract gate,
and the chat (provider surface, agentic loop, loadout, documents, inspector).

---

## 4. Try the TUI API from the CLI — **no AWS** (discovery)

`list` / `describe` / `skills` / `status` / `whatsnew` / `changelog` / `explore` read the
manifest and never call AWS:

```bash
sg aws s3 tui api list                      # the APIs + actions this area exposes
sg aws s3 tui api describe sg-aws.s3 --json # the manifest: actions, tiers, scopes, JSON Schemas
sg aws s3 tui api skills   sg-aws.s3 api    # the SKILL doc the model reads
sg aws s3 tui api status   sg-aws.s3        # "now what?" — health + available actions + recent changes
sg aws s3 tui api whatsnew sg-aws.s3        # the change log
sg aws s3 tui api explore                   # the Swagger-style Textual explorer (↑/↓, i=invoke)
```

The **explorer** lists every registered action; highlight one to see its JSON Schema +
scope; press `i` (or Enter) to invoke it through the execution center and see the result.

---

## 5. Try invoking + the chat — **needs AWS**

`invoke` and the live chat make real calls (resolve creds via your active `sg` context):

```bash
# invoke a read-only S3 action (real S3) — gated + audited through the execution center
sg aws s3 tui api invoke sg-aws.s3 list_buckets
sg aws s3 tui api invoke sg-aws.s3 list_objects --params '{"bucket":"my-bucket","prefix":"logs/"}'
sg aws s3 tui api invoke sg-aws.s3 list_objects --params '{"bucket":"my-bucket"}' --dry-run

# the chat (real Bedrock Nova):
sg aws bedrock chat tui                         # plain streaming chat
sg aws bedrock chat tui --model pro             # pick a Nova tier
sg aws bedrock chat tui --context ./snapshot.md # seed context to talk about
sg aws bedrock chat tui --tools 'core.vfs:read' # TOOL-ENABLED → the agentic (non-streaming) loop
```

### In the chat (keybindings)
```
Enter  send            ^O  model picker        F1  help
⇧Enter newline         ^B  capture dev brief   F2  inspector (request/response + tool calls)
Esc    stop            ^G  tools (loadout)      ^↑/^↓  inspector prev/next
^L     clear           ^D  attach a document    ^S  export · ^T theme · ^Q quit
```
- **`^G` (tools)** opens the loadout picker — cycle each API `off → read → write → *`,
  Enter applies. Granting tools flips the chat to the agentic loop.
- **`^D` (attach)** opens the document picker — type a path; the file rides your next
  message (pdf/txt/md/csv/docx/html/xls(x), ≤ 4.5 MB). A chip row shows what's attached.
- **`F2` (inspector)** shows the exact Converse request/response per turn **and** the tool
  calls the model made (✓/✗ · name · input · result) with `N model · M tools` cost.

---

## 6. Try it **headless, without AWS** (Python) — the reproducible path

Run these from the repo root (`PYTHONPATH=. python`), or in a pytest. They use the same
in-memory doubles the tests do.

### a) Drive the S3 provider (no AWS)
```python
from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider import S3__Tui_Api__Provider

client   = S3__AWS__Client__In_Memory().add_bucket('demo').add_object('demo', 'logs/a.txt', b'hi')
provider = S3__Tui_Api__Provider(client=client)
print(provider.manifest().json()['actions'][1]['input_schema'])           # real JSON Schema
print(provider.dispatch('list_objects', {'bucket': 'demo', 'recursive': True}).json())
```

### b) The VFS core tool (Python 3.12 + `memory_fs`)
```python
from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider import Vfs__Tui_Api__Provider
vfs = Vfs__Tui_Api__Provider()
vfs.dispatch('vfs.write', {'path': 'notes.md', 'content': 'the answer is 42'})
print(vfs.dispatch('vfs.read', {'path': 'notes.md'}).json())              # {'ok': True, 'data': {'result': 'the answer is 42'}}
print(vfs.state())                                                        # {'files': ['notes.md']}
```

### c) The agentic tool loop — scripted, no Bedrock
```python
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine        import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory      import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue            import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider                 import S3__Tui_Api__Provider
from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center       import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler     import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver    import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry               import Tui_Api__Registry

registry  = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo')))
resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path='/tmp/scopes.json'))
center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
builder   = Bedrock__Tool_Config__Builder()
granted   = Tui_Api__Loadout__Assembler().granted_actions(
                Tui_Api__Loadout__Assembler().from_tools('sg-aws.s3:read'), registry, resolver)
tool_config, name_map = builder.build(granted)

source = Bedrock__Chat__In_Memory()                                       # script the model: call a tool, then answer
source.scripted_turns = [
    {'stop_reason': 'tool_use',
     'content': [{'toolUse': {'toolUseId': 't1', 'name': builder.tool_name('sg-aws.s3', 'list_buckets'), 'input': {}}}],
     'input_tokens': 100, 'output_tokens': 20, 'latency_ms': 200},
    {'stop_reason': 'end_turn', 'content': [{'text': 'You have one bucket: demo.'}],
     'input_tokens': 150, 'output_tokens': 30, 'latency_ms': 250},
]
engine  = Bedrock__Chat__Engine(source=source)
session = engine.new_session(region='us-east-1', model_alias='lite')
turn    = engine.send_turn_agentic(session, 'how many buckets?', registry, center, tool_config, name_map)
print(session.messages[-1].text)                                          # 'You have one bucket: demo.'
print(turn.model_calls, turn.tool_calls, [str(c.action_ref) for c in center.log])   # 2 1 ['list_buckets']
```

### d) Snapshot the explorer (Textual, no AWS)
Run a headless render and save an SVG (convert to PNG with `cairosvg` if you want an image):
```python
import asyncio
from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Explorer import Tui_Api__Explorer
# build a registry like (a), then:
async def shot():
    app = Tui_Api__Explorer(registry=registry)
    async with app.run_test(size=(124, 38)) as pilot:
        await pilot.pause(); app.save_screenshot('/tmp/explorer.svg')
asyncio.run(shot())
```

---

## 7. What needs AWS vs not

| Works with **no AWS** | Needs **AWS creds** |
|---|---|
| `tui api list / describe / skills / status / whatsnew / changelog / explore` | `tui api invoke …` (real S3) |
| all the tests (in-memory) | the live chat `sg aws bedrock chat tui` (real Bedrock Nova) |
| every Python snippet in §6 | |

---

## 8. Known setup gaps / follow-ups

- **`memory_fs` is not yet a declared dependency.** The VFS core tool imports it and the
  chat's `--tools core.vfs:*` needs it. Install it manually (`pip install memory-fs`) for
  now. Declaring it as an **optional extra** (so it stays out of the Lambda/Fargate image)
  is a packaging/DevOps decision — tracked, not yet done.
- **No-TTY / piped chat** runs a single non-stream turn from stdin (no tools); the agentic
  loop needs an interactive TTY.
- **Deferred UI niceties:** an interactive VFS-seeding flow (`--vfs-seed <dir>`) and a
  dedicated per-session "context docs" panel — the functional paths exist (attach a doc, or
  seed text via `--context`).

---

## 9. Where it all lives

| Thing | Path |
|---|---|
| TUI API contract / registry / execution center / tokens / loadout | `sgraph_ai_service_playwright__cli/tui/tool_api/` |
| VFS core tool | `…/tui/tool_api/core/vfs/` |
| Explorer + loadout modal | `…/tui/tool_api/screens/` |
| S3 provider (first real provider) | `…/aws/s3/tui_api/` |
| Bedrock chat (engine, screens, tui_api provider, doc/tool glue) | `…/aws/bedrock/tui/` |
| The standard + the slice plans | `team/humans/dinis_cruz/claude-code-web/05/21/14/v0.2.36__tui-api-standard/` |
| The Bedrock chat pack (architecture / UX / plan) | `…/05/21/10/v0.2.36__bedrock-chat-tui-pack/` |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
