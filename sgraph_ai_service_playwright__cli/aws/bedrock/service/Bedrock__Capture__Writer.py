# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Capture__Writer
# Writes Bedrock interaction artefacts to a local directory tree under
# ~/.sg/aws/bedrock/.
#
# Writer-interface-shaped: when a vault-backed writer is introduced (v0.3.x),
# swapping Bedrock__Capture__Writer for Bedrock__Vault__Writer will be a single
# constructor change at call sites — not a verb-level rewrite.
#
# Files are written with 0600 permissions (owner-only, matching the credential
# store convention from v0.2.28).
#
# Layout:
#   chat interactions  → ~/.sg/aws/bedrock/chat/<ISO-day>/<run-id>.json
#   agent definitions  → ~/.sg/aws/bedrock/agents/<name>/definition.json
#   agent sessions     → ~/.sg/aws/bedrock/agents/<name>/sessions/<session-id>/trace.json
#   agent memory       → ~/.sg/aws/bedrock/agents/<name>/memory/<scope>/<snapshot-id>.json
#   browser sessions   → ~/.sg/aws/bedrock/tools/browser/<session-id>/actions.json
#   code-int sessions  → ~/.sg/aws/bedrock/tools/code-interpreter/<session-id>/run.json
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import stat
from pathlib                                                                     import Path

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

_DEFAULT_ROOT = Path.home() / '.sg' / 'aws' / 'bedrock'


class Bedrock__Capture__Writer(Type_Safe):
    root: str                                                                     # Base capture root; defaults to ~/.sg/aws/bedrock

    def capture_root(self) -> Path:                                              # Returns the effective root Path
        return Path(self.root) if self.root else _DEFAULT_ROOT

    # ── Chat ─────────────────────────────────────────────────────────────────

    def chat_path(self, iso_day: str, run_id: str) -> Path:                      # Path for one chat interaction record
        return self.capture_root() / 'chat' / iso_day / f'{run_id}.json'

    def write_chat(self, iso_day: str, run_id: str, payload: dict) -> Path:      # Persist a chat record; returns the path written
        path = self.chat_path(iso_day, run_id)
        self.write_json(path, payload)
        return path

    # ── Agent ────────────────────────────────────────────────────────────────

    def agent_definition_path(self, agent_name: str) -> Path:                   # Path for an agent definition
        return self.capture_root() / 'agents' / agent_name / 'definition.json'

    def write_agent_definition(self, agent_name: str, payload: dict) -> Path:   # Persist an agent definition
        path = self.agent_definition_path(agent_name)
        self.write_json(path, payload)
        return path

    def agent_session_path(self, agent_name: str, session_id: str) -> Path:     # Path for one agent session trace
        return self.capture_root() / 'agents' / agent_name / 'sessions' / session_id / 'trace.json'

    def write_agent_session(self, agent_name: str, session_id: str, payload: dict) -> Path:
        path = self.agent_session_path(agent_name, session_id)
        self.write_json(path, payload)
        return path

    def agent_memory_path(self, agent_name: str, scope: str, snapshot_id: str) -> Path:
        return self.capture_root() / 'agents' / agent_name / 'memory' / scope / f'{snapshot_id}.json'

    def write_agent_memory(self, agent_name: str, scope: str, snapshot_id: str, payload: dict) -> Path:
        path = self.agent_memory_path(agent_name, scope, snapshot_id)
        self.write_json(path, payload)
        return path

    # ── Tool browser ─────────────────────────────────────────────────────────

    def browser_session_path(self, session_id: str) -> Path:                    # Folder for a browser session
        return self.capture_root() / 'tools' / 'browser' / session_id

    def write_browser_action(self, session_id: str, payload: dict) -> Path:     # Append an action record to the session
        path = self.browser_session_path(session_id) / 'actions.json'
        self.write_json(path, payload)
        return path

    # ── Tool code-interpreter ────────────────────────────────────────────────

    def code_interpreter_session_path(self, session_id: str) -> Path:           # Folder for a code-interpreter session
        return self.capture_root() / 'tools' / 'code-interpreter' / session_id

    def write_code_run(self, session_id: str, payload: dict) -> Path:           # Persist a code execution record
        path = self.code_interpreter_session_path(session_id) / 'run.json'
        self.write_json(path, payload)
        return path

    # ── Core writer ──────────────────────────────────────────────────────────

    def write_json(self, path: Path, payload: dict) -> None:                    # Write a JSON file at 0600 perms; creates parents
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, indent=2, default=str)
        path.write_text(data, encoding='utf-8')
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)                             # 0600 — owner read/write only
