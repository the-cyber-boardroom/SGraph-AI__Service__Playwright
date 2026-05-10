# End-to-end example: driving sgit through Claude Code

A real session that exercises the whole stack — model, parser, tool execution, multi-step reasoning, error recovery, cross-machine collaboration. If you can reproduce this, your setup is solid.

This was the use case that motivated the whole exercise: agentic tool use was the thing missing from earlier configurations, and without it the local setup wasn't actually useful for development work. With it working, it is.

## What `sgit` is

`sgit` is a zero-knowledge encrypted vault tool with Git-like semantics — `init`, `commit`, `push`, `pull`, `status`. Vaults sync via a remote server but contents are encrypted client-side. For this exercise, what matters is that it's:

- A real CLI tool installed in a Python venv
- Has its own command syntax (different from Git in some specifics)
- Operates on a directory tree
- Has stateful interactions with a remote (push/pull)

It's a good stress test because driving it requires the model to:

1. Find the binary (it's in a venv, not on PATH)
2. Discover the working directory layout
3. Read tool output and act on it (status messages, error messages)
4. Recover from invalid command syntax
5. Sequence operations correctly (commit before push, pull before push when divergent)
6. Read file contents and integrate them into the conversation

## What "working" looks like

The session below is the actual transcript. Annotations highlight the agentic behaviors worth noticing.

### Setup state

Before starting, the EC2 instance had:

- A Python venv at `~/claude-session-venv/` with `sgit` installed
- A vault at `~/_vaults/new-vault/` with one file (`message-from-claude.txt`) committed in a previous session and pushed
- (On the user's laptop, in parallel) a clone of the same vault to which they had added a file (`new-file.txt`) with content "this is a message in reply, and the answer is 42 :)" and pushed

Goal: have Claude Code, running locally, navigate this state — discover the vault, push the local commit, then pull the laptop's changes, then read the new file.

### The transcript (abridged)

```
> hi you are using sgit inside our current venv can you see the vault we have inside the _vaults folder?

● [Lists ~/, finds _vaults/, lists _vaults/, finds new-vault/, lists new-vault/, finds .sg_vault and message-from-claude.txt]
● I can see there's a vault in the _vaults folder...
```

**What worked:** Multi-step exploration without prompting. The user asked one question; the model autonomously made four tool calls to fully characterize the directory structure before answering. This is the agent loop functioning.

```
> ok so inside that folder, can you execute the command sgit --token aws push

● Bash(cd _vaults/new-vault && sgit --token aws push)
  ⎿  Error: Exit code 127
     /bin/bash: line 1: sgit: command not found
```

**What worked:** First attempt with the literal command. Got `command not found` because the venv wasn't activated.

```
● Bash(source claude-session-venv/bin/activate && which sgit)
  ⎿  /home/ssm-user/claude-session-venv/bin/sgit
```

**What worked:** The model correctly diagnosed the problem (venv not activated), tried to activate it, and used `which` to confirm location. This is the kind of reasoning that requires actually understanding tool output, not just dispatching.

```
● Bash(cd _vaults/new-vault && source ../claude-session-venv/bin/activate && sgit --token aws push)
  ⎿  Error: Exit code 1
     /bin/bash: line 1: ../claude-session-venv/bin/activate: No such file or directory
```

**What it got wrong:** Relative path math. After `cd _vaults/new-vault`, the venv is at `../../claude-session-venv`, not `../claude-session-venv`.

```
● Bash(pwd && ls -la)
● [...corrects path...]
● Bash(cd _vaults/new-vault && source ../../claude-session-venv/bin/activate && sgit --token aws push)
  ⎿  Error: Exit code 1
     Pushing to default...
       ▸ Checking for uncommitted changes
     error: Working directory has uncommitted changes. Commit your changes before pushing.
```

**What worked:** Recovered from the path mistake by re-checking working directory. Then sgit ran successfully but refused to push because of uncommitted changes. The model parsed the error message:

```
● I can see what's happening now. The sgit command is working, but it's preventing 
  the push because there are uncommitted changes...
```

```
● Bash(source ../../claude-session-venv/bin/activate && sgit commit -m "Add Claude's test message file")
  ⎿  Error: Exit code 2
     usage: sgit-ai [-h] [--version] [--base-url BASE_URL] [--token TOKEN]
                    [--debug] [--vault PATH]
                    {version,update,help,clone,init,create,...} ...
     sgit-ai: error: unrecognized arguments: -m
```

**What it got wrong:** Assumed Git-like syntax. `sgit commit -m "msg"` doesn't work; sgit doesn't take `-m`.

**What worked:** Read the usage output, noticed `-m` wasn't in the accepted args, and retried without it:

```
● Bash(source ../../claude-session-venv/bin/activate && sgit commit)
  ⎿  Committed 1 file(s) to branch-clone-5e2eab4.
       Commit: obj-cas-imm-5717ea355656
```

This is the real test of agentic behavior. A non-agentic model would have looped on `sgit commit -m "..."` until you stopped it. This one read the error, adjusted, and recovered.

```
● Bash(source ../../claude-session-venv/bin/activate && sgit push)
  ⎿  Pushing to default...
       ▸ Checking for uncommitted changes
       ▸ First push — uploading vault structure
     [...success...]
```

Push worked. First half of the exercise complete.

```
> ok, now can you do an sgit pull?

● Bash(source ../../claude-session-venv/bin/activate && sgit status)
  ⎿  On branch: branch-clone-5e2eab40da0105af
       Remote: diverged: 2 ahead, 1 behind — run: sgit pull first, then sgit push
       Nothing to commit, working tree clean.
```

**What worked:** Status check before pulling, parsed "diverged: 2 ahead, 1 behind" correctly, decided pull was the right next step.

```
● Bash(source ../../claude-session-venv/bin/activate && sgit pull)
  ⎿  Pulling from default...
     [...]
     Fast-forward merge: +1 file
```

```
> can you read that file?

● [Read ~/_vaults/new-vault/new-file.txt]
● File: new-file.txt
  1 │ this is a message in reply, and the answer is 42 :)

  This appears to be a response to the previous interaction, with a reference 
  to the famous "answer to life, the universe, and everything" from Douglas Adams' 
  "The Hitchhiker's Guide to the Galaxy"...
```

**What worked:** Identified the new file from the pull output, read it, and integrated the contents with cultural context.

### And then the killer test

```
> can you write a quick debrief of what just happened and what have done with sgit?

● [Writes a debrief covering the operations performed]
```

Solid debrief, but generic — it didn't mention the cross-machine workflow.

```
> including the workflow where (in a previous session) you created the vault, 
  added a file to it, did a commit, then a push, the (on this session) ... 
  I then on my laptop , cloned the repo, saw your file, added a new file, 
  created a commit, pushed .... (then you in this session), pulled , saw a 
  new file, and printed the file contents

● [Writes a structured debrief with three labeled phases:
   Phase 1: Initial Setup and File Creation (previous session)
   Phase 2: Remote Collaboration (on your laptop)
   Phase 3: Synchronization and Verification (this session)]
```

**What worked, and this is the genuinely impressive part:** The model correctly distinguished three actors across two machines and three time periods, even though Phases 1 and 3 are both "Claude Code instances" and Phase 2 is "the human user." Following that structure correctly is not a stochastic-parrot move — it requires actually modeling the workflow.

## Why this transcript matters

It exercises every layer of the stack:

| Layer | Verified by |
|-------|-------------|
| vLLM serving the model | Every response that came back |
| `qwen3_coder` tool-call parser | Every `Bash(...)` indicator (vs. JSON-as-text) |
| Claude Code agent loop | Multi-step exploration, sequencing, error recovery |
| `--dangerously-skip-permissions` | No interactive prompts blocking the loop |
| `CLAUDE_CODE_ATTRIBUTION_HEADER=0` | Each turn took ~2-5 seconds, not 15+ |
| Context window | Whole session fit comfortably in 32k (later confirmed in 64k) |

If you can run a session like this, with similar agentic behavior, the setup is genuinely working. If you can't — if you see JSON in `content` instead of `Bash(...)`, or if the model loops on the same broken command, or if simple turns take 30 seconds — go back to `02-troubleshooting-and-tuning.md` and find the broken layer.

## How to reproduce something similar

You don't need sgit specifically. Any tool with these properties is a good test:

- Has a CLI binary in a non-PATH location (so the model has to discover it)
- Returns informative error messages (so the model can recover)
- Has stateful interactions (so the model has to sequence operations)
- Is unfamiliar enough that the model can't just run on memorized commands

Examples that would work as well:
- Any custom internal CLI tool you have
- A new release of a tool the model hasn't seen
- A multi-step workflow with `terraform`, `kubectl`, or `aws` CLI in an unusual configuration
- Driving an interactive REPL from non-interactive shell calls

Bad tests:
- "Run `ls -la`" — too easy, no reasoning required
- "Write a Python function to..." — pure code generation, no tool use
- Anything where the model can succeed by recalling memorized syntax

## Anti-patterns that will look like success but aren't

A few transcripts that *look* like working tool use but don't actually prove the stack:

**The model writes a tool call as JSON but Claude Code never executes it:**

```
● {
    "name": "Bash",
    "arguments": { "command": "pwd" }
  }
```

No `● Bash(pwd)` indicator, no command output. This is the failure mode from Lesson 1 in `03-experiments-and-lessons.md`. Tool calls are landing in `content`, not `tool_calls`.

**The model claims to have done something it didn't:**

```
> Run pwd
● [no actual tool call]
● The current working directory is /home/ec2-user.
```

Pure hallucination. The model didn't actually run `pwd`; it made up a plausible path. This happens when tool execution is failing silently and the model is filling in the blank. Verify by asking for something the model can't guess (e.g., contents of a file you just created with random content).

**The model gets confused after one tool call:**

```
> List the files in the home directory
● Bash(ls)
  ⎿  [output]
> What did the last command output?
● I don't have access to tools that would let me see the previous command's output...
```

This is a sign that tool *results* aren't being threaded back into the conversation correctly. Check that vLLM is returning streaming responses properly and Claude Code is reassembling them.

If any of these show up in your testing, fix them before relying on the setup for real work.
