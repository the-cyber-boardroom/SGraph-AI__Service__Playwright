# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Privilege__Resolver
# Two jobs: (1) do the caller's GRANTS cover an action's scope (the SG/Role gate)?
# (2) is an action's backing PRIVILEGE present — and if not, what's the actionable hint?
# SG_ROLE / IAM_ROLE map down to a creds scope (aws/creds); ENV is checkable; the rest
# (IAM_POLICY / VAULT_KEY / NETWORK) aren't verifiable offline — AWS enforces at call
# time, so v1 doesn't block on them (decision #1: presence check + print-policy on miss).
# Pure — reads the creds catalogue + env; no boto3, no STS call here.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue       import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Priv_Kind     import Enum__Tui_Api__Priv_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action    import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Privilege import Schema__Tui_Api__Privilege
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Token             import Tui_Api__Token


class Tui_Api__Privilege__Resolver(Type_Safe):
    creds_catalogue : Creds__Scope__Catalogue                                     # inject one with catalogue_path in tests
    token           : Tui_Api__Token

    def grants_cover(self, grants, action: Schema__Tui_Api__Action, now: float = None) -> bool:
        moment = time.time() if now is None else now
        for grant in grants:
            if self.token.is_expired(grant, moment):
                continue
            if self.token.covers(grant, action.scope):
                return True
        return False

    def holds(self, privilege: Schema__Tui_Api__Privilege) -> bool:               # can we positively confirm the backing grant?
        kind = privilege.kind
        if kind in (Enum__Tui_Api__Priv_Kind.SG_ROLE, Enum__Tui_Api__Priv_Kind.IAM_ROLE):
            return self.creds_catalogue.scope_get(str(privilege.ref)) is not None
        if kind == Enum__Tui_Api__Priv_Kind.ENV:
            return bool(os.environ.get(str(privilege.ref)))
        return True                                                               # not verifiable offline — AWS enforces at call time

    def hint(self, privilege: Schema__Tui_Api__Privilege) -> str:                 # the actionable message to show when blocked
        kind = privilege.kind
        ref  = str(privilege.ref)
        if kind in (Enum__Tui_Api__Priv_Kind.SG_ROLE, Enum__Tui_Api__Priv_Kind.IAM_ROLE):
            return (f'add the creds scope: sg aws creds scope add {ref} <role-arn>'
                    f'  (then assume it: sg aws creds assume {ref})')
        if kind == Enum__Tui_Api__Priv_Kind.IAM_POLICY:
            return self.minimal_policy(ref)
        if kind == Enum__Tui_Api__Priv_Kind.ENV:
            return f'set environment variable {ref}'
        if kind == Enum__Tui_Api__Priv_Kind.VAULT_KEY:
            return f'unlock vault key {ref}'
        return privilege.note or f'grant required: {ref}'

    def missing(self, privilege: Schema__Tui_Api__Privilege) -> str:              # '' if satisfied, else the hint
        return '' if self.holds(privilege) else self.hint(privilege)

    def minimal_policy(self, action_ref: str) -> str:                             # the least-privilege IAM policy for one action
        return json.dumps({'Version'  : '2012-10-17',
                          'Statement': [{'Effect': 'Allow', 'Action': action_ref, 'Resource': '*'}]}, indent=2)
