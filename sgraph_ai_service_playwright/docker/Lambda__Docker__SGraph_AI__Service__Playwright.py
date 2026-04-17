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
# `create_lambda_function_url()` needs TWO resource-policy statements, not one:
#   • FunctionURLAllowPublicAccess — lambda:InvokeFunctionUrl (osbot_aws helper)
#   • FunctionURLAllowInvokeAction — lambda:InvokeFunction    (added here)
# The AWS Console banner "Your function URL auth type is NONE, but is missing
# permissions required for public access" confirms both are required — adding
# only InvokeFunctionUrl still yields 403 Forbidden on the URL. osbot_aws's
# `function_url_create_with_public_access()` only adds InvokeFunctionUrl, so
# we call `permission_add()` again for the InvokeFunction statement and fail
# loudly if the helper's silent-error shape ({'error': ...}) comes back.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.helpers.duration.Duration                                              import Duration
from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Env                                                              import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


LAMBDA_MEMORY_MB                      = 5120                                            # Production-tuned; do not reduce (see header)
LAMBDA_ARCHITECTURE                   = 'x86_64'                                        # GH Actions builds x86_64 images
LAMBDA_TIMEOUT_SECS                   = 300                                             # 5 min — sequences + browser launches overflow the 60s default

FUNCTION_URL_INVOKE_MODE              = 'BUFFERED'
FUNCTION_URL_AUTH_TYPE                = 'NONE'                                          # Public URL, paired with the two policy statements below
FUNCTION_URL_INVOKE_STATEMENT_ID      = 'FunctionURLAllowInvokeAction'                  # Second statement — lambda:InvokeFunction (AWS requires both actions)
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

    def create_lambda_function_url(self):                                               # Delete (idempotent) → osbot_aws public-access create → add second InvokeFunction statement
        with Duration(prefix='[create_lambda_function_url] |'):
            lambda_function = self.lambda_function()

            if lambda_function.function_url_exists():                                   # 1. Idempotent delete
                lambda_function.function_url_delete()
                print('[create_lambda_function_url] step 1/3: deleted existing URL config')
            else:
                print('[create_lambda_function_url] step 1/3: no existing URL config')

            url_result = lambda_function.function_url_create_with_public_access(invoke_mode=FUNCTION_URL_INVOKE_MODE)     # 2. URL + FunctionURLAllowPublicAccess (lambda:InvokeFunctionUrl)
            print(f'[create_lambda_function_url] step 2/3: created URL + public-access statement: {url_result}')

            invoke_permission = lambda_function.permission_add(function_arn            = lambda_function.function_arn()        ,     # 3. Second statement — lambda:InvokeFunction (AWS rejects public URL calls without this too)
                                                                statement_id           = FUNCTION_URL_INVOKE_STATEMENT_ID      ,
                                                                action                 = FUNCTION_URL_INVOKE_ACTION            ,
                                                                principal              = FUNCTION_URL_PRINCIPAL                ,
                                                                function_url_auth_type = FUNCTION_URL_AUTH_TYPE                )
            if isinstance(invoke_permission, dict) and invoke_permission.get('error'):                                            # permission_add swallows API errors into {'error': ...} — fail loudly so CI catches it
                raise RuntimeError(f'permission_add (InvokeFunction) failed: {invoke_permission["error"]}')
            print(f'[create_lambda_function_url] step 3/3: added invoke-action statement: {invoke_permission}')

            function_url_value = url_result.get('function_url_create', {}).get('FunctionUrl')
            return dict(function_url         = function_url_value  ,
                        auth_type            = FUNCTION_URL_AUTH_TYPE,
                        url_policy           = url_result.get('function_set_policy'),
                        invoke_permission    = invoke_permission   )

    def update_lambda_function(self):
        return self.lambda_function().update_lambda_image_uri(self.image_uri())

    def function_url(self):
        return self.lambda_function().function_url()
