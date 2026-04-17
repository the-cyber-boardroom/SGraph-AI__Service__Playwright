# ═══════════════════════════════════════════════════════════════════════════════
# Lambda__Docker__SGraph_AI__Service__Playwright — create/update Lambda from Docker image
#
# Production-tuning values carried forward from OSBot-Playwright:
#   memory_size   = 5120 MB  (osbot_aws reads `memory_size`, NOT `memory` — the
#                             wrong attr silently falls back to 512 MB and
#                             Playwright OOMs at cold start with Runtime.ExitError)
#   architecture  = x86_64   (GH Actions builds x86_64 images)
#   timeout       = 300 s    (sequences + browser launches overflow the 60s default)
#
# `set_lambda_env_vars()` propagates the SG_PLAYWRIGHT__* + FAST_API__AUTH__*
# secrets from the CI environment into the Lambda's environment, pinning
# DEPLOYMENT_TARGET=lambda so the in-process detector sees the correct target.
#
# `create_lambda_function_url()` — AuthType=NONE needs TWO policy statements
# (per https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html, required
# for all URLs created after October 2025):
#   1. FunctionURLAllowPublicAccess — lambda:InvokeFunctionUrl with the
#      StringEquals condition on lambda:FunctionUrlAuthType=NONE
#      (osbot_aws's function_url_create_with_public_access() adds this)
#   2. FunctionURLInvokeAllowPublicAccess — lambda:InvokeFunction with the
#      Bool condition on lambda:InvokedViaFunctionUrl=true
#      (must go via boto3 — osbot_aws.permission_add() has no parameter for
#      InvokedViaFunctionUrl, and passing FunctionUrlAuthType on an
#      InvokeFunction statement produces the wrong condition)
# ═══════════════════════════════════════════════════════════════════════════════

import boto3
from botocore.exceptions                                                                import ClientError

from osbot_utils.helpers.duration.Duration                                              import Duration
from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Env                                                              import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


LAMBDA_MEMORY_MB                      = 5120                                            # Production-tuned; do not reduce (see header)
LAMBDA_ARCHITECTURE                   = 'x86_64'                                        # GH Actions builds x86_64 images
LAMBDA_TIMEOUT_SECS                   = 300                                             # 5 min — sequences + browser launches overflow the 60s default

FUNCTION_URL_INVOKE_MODE              = 'BUFFERED'
FUNCTION_URL_AUTH_TYPE                = 'NONE'                                          # Public URL, paired with the two policy statements
FUNCTION_URL_INVOKE_STATEMENT_ID      = 'FunctionURLInvokeAllowPublicAccess'            # Second statement — lambda:InvokeFunction with InvokedViaFunctionUrl condition
FUNCTION_URL_INVOKE_ACTION            = 'lambda:InvokeFunction'
FUNCTION_URL_PRINCIPAL                = '*'


class Lambda__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def create_lambda(self, delete_existing=False, wait_for_active=False):
        with Duration(prefix='[create_lambda] | delete and create:'):                   # No outer try/except: errors must propagate so CI surfaces the real failure
            lambda_function              = self.lambda_function()
            lambda_function.image_uri    = self.image_uri()
            lambda_function.architecture = LAMBDA_ARCHITECTURE
            lambda_function.memory_size  = LAMBDA_MEMORY_MB                             # osbot_aws reads memory_size (see create_kwargs → MemorySize)
            lambda_function.timeout      = LAMBDA_TIMEOUT_SECS

            self.set_lambda_env_vars(lambda_function)                                   # Propagate CI secrets → Lambda env

            if delete_existing:
                lambda_function.delete()

            create_result = lambda_function.create()
            pprint(create_result)

            if wait_for_active:
                with Duration(prefix='[create_lambda] | wait for active:'):
                    lambda_function.wait_for_state_active(max_wait_count=80)

            function_url = self.create_lambda_function_url()
            return dict(create_result=create_result, function_url=function_url)

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

    def create_lambda_function_url(self):                                               # Delete (idempotent) → osbot_aws public-access create → add second InvokeFunction statement via boto3
        with Duration(prefix='[create_lambda_function_url] |'):
            lambda_function = self.lambda_function()
            function_name   = lambda_function.name

            if lambda_function.function_url_exists():                                   # 1. Idempotent delete of any previous URL config
                lambda_function.function_url_delete()
                print('[create_lambda_function_url] step 1/4: deleted existing URL config')
            else:
                print('[create_lambda_function_url] step 1/4: no existing URL config')

            url_result = lambda_function.function_url_create_with_public_access(invoke_mode=FUNCTION_URL_INVOKE_MODE)     # 2. URL + statement 1 (lambda:InvokeFunctionUrl + StringEquals lambda:FunctionUrlAuthType=NONE)
            print(f'[create_lambda_function_url] step 2/4: created URL + InvokeFunctionUrl statement: {url_result}')

            boto3_client = boto3.client('lambda', region_name=get_env('AWS_DEFAULT_REGION'))                              # 3. & 4. Second statement via boto3 — osbot_aws.permission_add doesn't pass InvokedViaFunctionUrl

            try:                                                                                                          # 3. Remove stale statement (idempotent)
                boto3_client.remove_permission(FunctionName = function_name                  ,
                                                StatementId  = FUNCTION_URL_INVOKE_STATEMENT_ID)
                print('[create_lambda_function_url] step 3/4: removed stale InvokeFunction statement')
            except ClientError as error:
                if error.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                print('[create_lambda_function_url] step 3/4: no stale InvokeFunction statement')

            invoke_permission = boto3_client.add_permission(FunctionName           = function_name                  ,     # 4. Statement 2: lambda:InvokeFunction + Bool lambda:InvokedViaFunctionUrl=true
                                                             StatementId            = FUNCTION_URL_INVOKE_STATEMENT_ID,
                                                             Action                 = FUNCTION_URL_INVOKE_ACTION      ,
                                                             Principal              = FUNCTION_URL_PRINCIPAL          ,
                                                             InvokedViaFunctionUrl  = True                            )
            print(f'[create_lambda_function_url] step 4/4: added InvokeFunction statement: {invoke_permission.get("Statement")}')

            function_url_value = url_result.get('function_url_create', {}).get('FunctionUrl')
            return dict(function_url      = function_url_value                          ,
                        auth_type         = FUNCTION_URL_AUTH_TYPE                      ,
                        url_policy        = url_result.get('function_set_policy')      ,
                        invoke_permission = invoke_permission.get('Statement')         )

    def update_lambda_function(self):
        return self.lambda_function().update_lambda_image_uri(self.image_uri())

    def function_url(self):
        return self.lambda_function().function_url()
