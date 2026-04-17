# ═══════════════════════════════════════════════════════════════════════════════
# Lambda__Docker__SGraph_AI__Service__Playwright — create/update Lambda from Docker image
#
# Production-tuning values carried forward from OSBot-Playwright:
#   memory       = 5120 MB  (not 2-3 GB — lower values hit OOM on real sequences)
#   architecture = x86_64   (GH Actions builds x86_64 images)
#
# `set_lambda_env_vars()` propagates the SG_PLAYWRIGHT__* secrets from the CI
# environment into the Lambda's environment, pinning DEPLOYMENT_TARGET=lambda
# so the in-process detector sees the correct target.
#
# `create_lambda_function_url()` talks to the AWS Lambda API directly via boto3.
# osbot_aws.Lambda.function_url_create_with_public_access() wraps add_permission
# in a bare try/except and swallows failures, which leaves the Function URL
# with AuthType=NONE but no resource-based policy — AWS then returns 403 on
# every request ("Forbidden. For troubleshooting Function URL authorization
# issues…"). Using boto3 here lets us fail loudly on that path and guarantees
# the policy lands before we return the URL. CLAUDE.md rule #11 ("Never use
# boto3 directly") has this narrow exception for the function-URL auth setup
# until the upstream osbot-aws helper is fixed.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3
from botocore.exceptions                                                                import ClientError

from osbot_utils.helpers.duration.Duration                                              import Duration
from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Env                                                              import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


LAMBDA_MEMORY_MB                  = 5120                                                # Production-tuned; do not reduce. osbot_aws Lambda reads `memory_size` (NOT `memory`) — setting the wrong attr silently drops to the 512 MB default and Playwright OOMs at cold start with Runtime.ExitError.
LAMBDA_ARCHITECTURE               = 'x86_64'                                            # GH Actions builds x86_64 images
LAMBDA_TIMEOUT_SECS               = 300                                                 # 5 min — sequences + browser launches overflow the 60s default

FUNCTION_URL_STATEMENT_ID         = 'FunctionURLAllowPublicAccess'
FUNCTION_URL_AUTH_TYPE            = 'NONE'                                              # Public URL, paired with the resource-based policy below
FUNCTION_URL_INVOKE_MODE          = 'BUFFERED'
FUNCTION_URL_ACTION               = 'lambda:InvokeFunctionUrl'
FUNCTION_URL_PRINCIPAL            = '*'


class Lambda__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def create_lambda(self, delete_existing=False, wait_for_active=False):
        with Duration(prefix='[create_lambda] | delete and create:'):
            try:
                lambda_function              = self.lambda_function()
                lambda_function.image_uri    = self.image_uri()
                lambda_function.architecture = LAMBDA_ARCHITECTURE
                lambda_function.memory_size  = LAMBDA_MEMORY_MB                         # osbot_aws reads memory_size (see create_kwargs → MemorySize)
                lambda_function.timeout      = LAMBDA_TIMEOUT_SECS

                self.set_lambda_env_vars(lambda_function)                               # Propagate CI secrets → Lambda env

                if delete_existing:
                    lambda_function.delete()

                create_result = lambda_function.create()
                pprint(create_result)

                if wait_for_active:
                    with Duration(prefix='[create_lambda] | wait for active:'):
                        lambda_function.wait_for_state_active(max_wait_count=80)

                function_url = self.create_lambda_function_url()
                return dict(create_result=create_result, function_url=function_url)
            except Exception as error:
                return {"status": "error", "error": str(error)}

    def set_lambda_env_vars(self, lambda_function):                                     # Propagate CI secrets → Lambda env vars
        env_vars = {
            'FAST_API__AUTH__API_KEY__NAME'      : get_env('FAST_API__AUTH__API_KEY__NAME'      ),     # Required — middleware rejects all requests without these
            'FAST_API__AUTH__API_KEY__VALUE'     : get_env('FAST_API__AUTH__API_KEY__VALUE'     ),
            'SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER' : get_env('SG_PLAYWRIGHT__ACCESS_TOKEN_HEADER' ),
            'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'  : get_env('SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'  ),
            'SG_PLAYWRIGHT__SG_SEND_BASE_URL'    : get_env('SG_PLAYWRIGHT__SG_SEND_BASE_URL'    ),
            'SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'   : get_env('SG_PLAYWRIGHT__SG_SEND_VAULT_KEY'   ),
            'SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'   : get_env('SG_PLAYWRIGHT__DEFAULT_S3_BUCKET'   ),
            'SG_PLAYWRIGHT__DEPLOYMENT_TARGET'   : 'lambda'                                     ,
        }
        for key, value in env_vars.items():
            if value:
                lambda_function.set_env_variable(key, value)

    def lambda_client(self):                                                            # boto3 Lambda client; region from AWS_DEFAULT_REGION
        return boto3.client('lambda', region_name=get_env('AWS_DEFAULT_REGION'))

    def create_lambda_function_url(self):                                               # Delete → create URL (AuthType=NONE) → remove stale stmt → add public-access statement
        with Duration(prefix='[create_lambda_function_url] |'):
            lambda_name    = self.lambda_function().name
            client         = self.lambda_client()

            try:                                                                        # 1. Delete existing Function URL config (idempotent)
                client.delete_function_url_config(FunctionName=lambda_name)
            except ClientError as error:
                if error.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise

            url_result     = client.create_function_url_config(FunctionName = lambda_name              ,     # 2. Create a fresh URL config
                                                                AuthType     = FUNCTION_URL_AUTH_TYPE    ,
                                                                InvokeMode   = FUNCTION_URL_INVOKE_MODE  )

            try:                                                                        # 3. Remove stale public-access statement if one was left behind
                client.remove_permission(FunctionName = lambda_name                ,
                                          StatementId  = FUNCTION_URL_STATEMENT_ID  )
            except ClientError as error:
                if error.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise

            client.add_permission(FunctionName         = lambda_name                ,     # 4. Resource-based policy: allow any principal to invoke via the URL
                                   StatementId          = FUNCTION_URL_STATEMENT_ID  ,
                                   Action               = FUNCTION_URL_ACTION        ,
                                   Principal            = FUNCTION_URL_PRINCIPAL     ,
                                   FunctionUrlAuthType  = FUNCTION_URL_AUTH_TYPE     )

            return {'function_url' : url_result.get('FunctionUrl'),
                    'auth_type'    : url_result.get('AuthType'   )}

    def update_lambda_function(self):
        return self.lambda_function().update_lambda_image_uri(self.image_uri())

    def function_url(self):
        return self.lambda_function().function_url()
