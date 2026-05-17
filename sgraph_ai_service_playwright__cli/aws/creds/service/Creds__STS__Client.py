# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Creds__STS__Client
# Thin STS boundary for assume_role.  Uses a client() seam so tests can
# substitute an in-memory fake without patching or mocking.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session      import Sg__Aws__Session


class Creds__STS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                           # cached session — injected or lazy-init via setup()

    def setup(self):                                                             # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                           # Single seam — override in subclass for in-memory tests
        self.setup()
        return self.session.boto3_client_from_context('sts')

    def assume_role(self, role_arn: str, session_name: str,
                    duration_seconds: int) -> dict:                             # Returns AccessKeyId/SecretAccessKey/SessionToken/Expiration
        sts  = self.client()
        resp = sts.assume_role(
            RoleArn         = role_arn,
            RoleSessionName = session_name,
            DurationSeconds = duration_seconds,
        )
        creds = resp['Credentials']
        return {
            'AccessKeyId'     : creds['AccessKeyId'],
            'SecretAccessKey' : creds['SecretAccessKey'],
            'SessionToken'    : creds['SessionToken'],
            'Expiration'      : str(creds['Expiration']),
        }

    def get_caller_identity(self) -> str:                                       # Returns ARN of the current caller for session naming
        try:
            resp = self.client().get_caller_identity()
            return resp.get('Arn', 'unknown')
        except Exception:
            return 'unknown'
