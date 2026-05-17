# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — IAM__AWS__Client
# Sole boto3 boundary for IAM role and policy operations. Every boto3 call for
# the iam sub-package lives here so Cli__Iam can stay pure Python + Type_Safe
# schemas and the in-memory test subclass has a small, well-defined surface.
#
# EXCEPTION — no osbot-aws IAM wrapper covers role + inline-policy CRUD at the
# time of writing. Using boto3 directly gives us one thin boundary.
# Migrate once osbot-aws IAM support stabilises.
#
# Mutation guard: callers check SG_AWS__IAM__ALLOW_MUTATIONS=1 before calling
# create_role / delete_role / put_inline_policy / attach_policy / detach_policy.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                         import Optional

import boto3                                                                         # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Role  import List__Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service      import Enum__IAM__Trust__Service
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Policy_Arn import Safe_Str__IAM__Policy_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Arn   import Safe_Str__IAM__Role_Arn
from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Role_Name  import Safe_Str__IAM__Role_Name
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Policy          import Schema__IAM__Policy
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role            import Schema__IAM__Role
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request  import Schema__IAM__Role__Create__Request
from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Response import Schema__IAM__Role__Create__Response
from sgraph_ai_service_playwright__cli.aws.iam.service.IAM__Trust_Policy__Builder   import IAM__Trust_Policy__Builder


class IAM__AWS__Client(Type_Safe):

    def client(self):                                                                # Single seam — subclass overrides for in-memory tests
        return boto3.client('iam')

    # ── read ──────────────────────────────────────────────────────────────────

    def list_roles(self, prefix: str = '') -> List__Schema__IAM__Role:
        iam    = self.client()
        result = List__Schema__IAM__Role()
        kwargs = {}
        if prefix:
            kwargs['PathPrefix'] = '/'                                               # IAM PathPrefix is path, not name — filter by name after listing
        paginator = iam.get_paginator('list_roles')
        for page in paginator.paginate(**kwargs):
            for raw in page.get('Roles', []):
                name = raw.get('RoleName', '')
                if prefix and not name.startswith(prefix):
                    continue
                result.append(self._parse_role_summary(raw))
        return result

    def get_role(self, role_name: str) -> Optional[Schema__IAM__Role]:
        try:
            iam   = self.client()
            resp  = iam.get_role(RoleName=role_name)
            role  = self._parse_role_summary(resp['Role'])
            self._load_inline_policies(role, iam)
            self._load_managed_policies(role, iam)
            return role
        except Exception:
            return None

    def role_exists(self, role_name: str) -> bool:
        return self.get_role(role_name) is not None

    # ── mutations ─────────────────────────────────────────────────────────────

    def create_role(self, request: Schema__IAM__Role__Create__Request) -> Schema__IAM__Role__Create__Response:
        trust_doc = IAM__Trust_Policy__Builder().build(request.trust_service)
        iam       = self.client()
        try:
            resp = iam.create_role(
                RoleName                 = str(request.role_name),
                AssumeRolePolicyDocument = trust_doc,
                Description              = request.description,
            )
            role_arn = resp['Role']['Arn']
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                existing = self.get_role(str(request.role_name))
                role_arn = str(existing.role_arn) if existing else ''
                created  = False
            else:
                return Schema__IAM__Role__Create__Response(
                    role_name = request.role_name,
                    role_arn  = Safe_Str__IAM__Role_Arn(''),
                    created   = False,
                    message   = str(e),
                )
        else:
            created = True

        if request.inline_policy is not None:
            self.put_inline_policy(str(request.role_name), request.policy_name,
                                   request.inline_policy)
        return Schema__IAM__Role__Create__Response(
            role_name = request.role_name,
            role_arn  = Safe_Str__IAM__Role_Arn(role_arn),
            created   = created,
            message   = 'created' if created else 'already exists',
        )

    def delete_role(self, role_name: str) -> bool:
        iam = self.client()
        try:
            for policy_name in self._list_inline_policy_names(role_name, iam):
                iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
            for arn in self._list_attached_policy_arns(role_name, iam):
                iam.detach_role_policy(RoleName=role_name, PolicyArn=arn)
            iam.delete_role(RoleName=role_name)
            return True
        except Exception:
            return False

    def put_inline_policy(self, role_name: str, policy_name: str,
                           policy: Schema__IAM__Policy) -> bool:
        doc = self._policy_to_json(policy)
        try:
            self.client().put_role_policy(RoleName      = role_name,
                                          PolicyName    = policy_name,
                                          PolicyDocument= doc)
            return True
        except Exception:
            return False

    def attach_managed_policy(self, role_name: str, policy_arn: str) -> bool:
        try:
            self.client().attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            return True
        except Exception:
            return False

    def detach_managed_policy(self, role_name: str, policy_arn: str) -> bool:
        try:
            self.client().detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            return True
        except Exception:
            return False

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_role_summary(self, raw: dict) -> Schema__IAM__Role:
        name     = raw.get('RoleName', '')
        arn      = raw.get('Arn', '')
        created  = str(raw.get('CreateDate', ''))
        last_used_raw = raw.get('RoleLastUsed', {})
        last_used = str(last_used_raw.get('LastUsedDate', '')) if last_used_raw else ''
        trust_doc = raw.get('AssumeRolePolicyDocument', {})
        if isinstance(trust_doc, str):
            import urllib.parse
            trust_doc = json.loads(urllib.parse.unquote(trust_doc))
        trust_service = self._infer_trust_service(trust_doc)
        return Schema__IAM__Role(
            role_name    = Safe_Str__IAM__Role_Name(name) if name else Safe_Str__IAM__Role_Name(''),
            role_arn     = Safe_Str__IAM__Role_Arn(arn)   if arn.startswith('arn:') else Safe_Str__IAM__Role_Arn(''),
            trust_service= trust_service,
            created_at   = created,
            last_used    = last_used,
        )

    def _infer_trust_service(self, trust_doc: dict) -> Enum__IAM__Trust__Service:
        for stmt in trust_doc.get('Statement', []):
            principal = stmt.get('Principal', {})
            service   = principal.get('Service', '') if isinstance(principal, dict) else ''
            try:
                return Enum__IAM__Trust__Service(service)
            except ValueError:
                continue
        return Enum__IAM__Trust__Service.LAMBDA

    def _load_inline_policies(self, role: Schema__IAM__Role, iam) -> None:
        names = self._list_inline_policy_names(str(role.role_name), iam)
        for name in names:
            try:
                doc = iam.get_role_policy(RoleName=str(role.role_name), PolicyName=name)
                policy_doc = doc.get('PolicyDocument', {})
                if isinstance(policy_doc, str):
                    policy_doc = json.loads(policy_doc)
                policy = self._parse_policy_doc(policy_doc)
                role.inline_policies.append(policy)
            except Exception:
                continue

    def _load_managed_policies(self, role: Schema__IAM__Role, iam) -> None:
        arns = self._list_attached_policy_arns(str(role.role_name), iam)
        for arn in arns:
            try:
                role.managed_policy_arns.append(Safe_Str__IAM__Policy_Arn(arn))
            except Exception:
                continue

    def _list_inline_policy_names(self, role_name: str, iam) -> list:
        names     = []
        paginator = iam.get_paginator('list_role_policies')
        for page in paginator.paginate(RoleName=role_name):
            names.extend(page.get('PolicyNames', []))
        return names

    def _list_attached_policy_arns(self, role_name: str, iam) -> list:
        arns      = []
        paginator = iam.get_paginator('list_attached_role_policies')
        for page in paginator.paginate(RoleName=role_name):
            for p in page.get('AttachedPolicies', []):
                arns.append(p.get('PolicyArn', ''))
        return arns

    def _parse_policy_doc(self, doc: dict) -> Schema__IAM__Policy:
        from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Schema__IAM__Statement  import List__Schema__IAM__Statement
        from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement            import Schema__IAM__Statement
        from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Action   import List__Safe_Str__Aws__Action
        from sgraph_ai_service_playwright__cli.aws.iam.collections.List__Safe_Str__Aws__Resource import List__Safe_Str__Aws__Resource
        from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Action          import Safe_Str__Aws__Action
        from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Resource        import Safe_Str__Aws__Resource
        stmts = List__Schema__IAM__Statement()
        for raw_stmt in doc.get('Statement', []):
            effect  = raw_stmt.get('Effect', 'Allow')
            raw_act = raw_stmt.get('Action', [])
            raw_res = raw_stmt.get('Resource', [])
            cond    = raw_stmt.get('Condition', {})
            actions   = List__Safe_Str__Aws__Action()
            resources = List__Safe_Str__Aws__Resource()
            for a in (raw_act if isinstance(raw_act, list) else [raw_act]):
                try:
                    actions.append(Safe_Str__Aws__Action(a))
                except Exception:
                    pass                                                              # Skip unparseable actions (e.g. bare "*" from pre-existing roles)
            has_wildcard = False
            for r in (raw_res if isinstance(raw_res, list) else [raw_res]):
                try:
                    resources.append(Safe_Str__Aws__Resource(r))
                    if r == '*':
                        has_wildcard = True
                except Exception:
                    pass
            stmt = Schema__IAM__Statement(
                effect                 = effect,
                actions                = actions,
                resources              = resources,
                allow_wildcard_resource= has_wildcard,
                condition_json         = json.dumps(cond) if cond else '',
            )
            stmts.append(stmt)
        return Schema__IAM__Policy(version=doc.get('Version', '2012-10-17'), statements=stmts)

    def _policy_to_json(self, policy: Schema__IAM__Policy) -> str:
        stmts = []
        for stmt in policy.statements:
            s = {
                'Effect'  : stmt.effect,
                'Action'  : [str(a) for a in stmt.actions],
                'Resource': [str(r) for r in stmt.resources],
            }
            if stmt.condition_json:
                s['Condition'] = json.loads(stmt.condition_json)
            stmts.append(s)
        return json.dumps({'Version': policy.version, 'Statement': stmts})
