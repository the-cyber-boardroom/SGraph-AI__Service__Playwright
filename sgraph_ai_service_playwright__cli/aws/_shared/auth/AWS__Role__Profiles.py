# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Role__Profiles
# The generic registry of per-family least-privilege role profiles. Families
# self-register their Schema__AWS__Role__Profile (one file each); this module renders a
# profile into an IAM policy document and the standard trust policy, and resolves a
# family's role ARN. Generic — knows nothing about any specific family beyond the small
# import list in _ensure_loaded(). Adding a section = a new profile file + one line here.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Role__Profile import Schema__AWS__Role__Profile

_REGISTRY : dict = {}                                                                # family → Schema__AWS__Role__Profile
_LOADED   : list = []                                                                # one-shot guard for _ensure_loaded


def register(profile : Schema__AWS__Role__Profile) -> None:
    _REGISTRY[str(profile.family)] = profile


def _ensure_loaded() -> None:
    if _LOADED:
        return
    _LOADED.append(True)
    # families self-register on import — one line per onboarded section:
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.iam import cf_role_profile  # noqa: F401
    from sgraph_ai_service_playwright__cli.sentinel.service    import Sentinel__Role__Profile  # noqa: F401


def get_profile(family : str):
    _ensure_loaded()
    return _REGISTRY.get(family)


def all_families() -> list:
    _ensure_loaded()
    return sorted(_REGISTRY.keys())


def role_arn(profile : Schema__AWS__Role__Profile, account_id : str) -> str:
    return f'arn:aws:iam::{account_id}:role/{profile.role_name}'


def policy_document(profile : Schema__AWS__Role__Profile) -> dict:                   # IAM policy JSON from the profile statements
    statements = []
    for s in profile.statements:
        statements.append({'Sid'      : str(s.sid),
                           'Effect'   : str(s.effect),
                           'Action'   : [str(a) for a in s.actions],
                           'Resource' : [str(r) for r in s.resources]})
    return {'Version': '2012-10-17', 'Statement': statements}


def trust_policy_document(account_id : str) -> dict:                                 # allow the account's identities to assume the role
    return {'Version'  : '2012-10-17',
            'Statement': [{'Effect'   : 'Allow',
                          'Principal' : {'AWS': f'arn:aws:iam::{account_id}:root'},
                          'Action'    : 'sts:AssumeRole'}]}


def service_trust_policy_document(services : list) -> dict:                          # execution-role trust for AWS service principals
    return {'Version'  : '2012-10-17',
            'Statement': [{'Effect'   : 'Allow',
                          'Principal' : {'Service': [str(s) for s in services]},
                          'Action'    : 'sts:AssumeRole'}]}


def trust_policy_for(profile : Schema__AWS__Role__Profile, account_id : str) -> dict:
    services = [str(s) for s in (profile.trust_services or [])]
    if services:                                                                     # execution role (e.g. Lambda@Edge): service-principal trust
        return service_trust_policy_document(services)
    return trust_policy_document(account_id)                                         # default: account-root assume-role trust
