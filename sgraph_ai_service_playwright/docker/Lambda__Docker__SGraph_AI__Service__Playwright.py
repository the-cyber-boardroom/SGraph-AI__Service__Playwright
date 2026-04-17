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
# DO NOT DELETE THE FUNCTION OR THE FUNCTION URL — CloudFront is wired to the
# URL's host UUID (`<uuid>.lambda-url.<region>.on.aws`). Deleting either the
# function or its URL config regenerates that UUID and breaks the CloudFront
# origin. The upsert path below updates image + configuration in place and
# only creates the Function URL when it does not already exist.
#
# Lambda update serialization — every Lambda update (image, configuration,
# permissions) flips the function to LastUpdateStatus=InProgress. Issuing a
# second update before it returns to Successful raises
# ResourceConflictException ("The operation cannot be performed at this time.
# An update is in progress for resource …"). We bracket each in-place update
# with wait_for_function_update_to_complete() so the image→config→url chain
# serialises correctly. osbot_aws's default (40 × 0.1s = 4s) is too short for
# a 5120MB Playwright image — bumped to 300 × 0.5s = 150s.
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
LAMBDA_UPDATE_MAX_ATTEMPTS            = 300                                             # 300 × 0.5s = 150s — image updates on 5120MB Playwright Lambdas can take 20-60s; osbot_aws's 40 × 0.1s default times out first
LAMBDA_UPDATE_WAIT_SECS               = 0.5

FUNCTION_URL_INVOKE_MODE              = 'BUFFERED'
FUNCTION_URL_AUTH_TYPE                = 'NONE'                                          # Public URL, paired with the two policy statements
FUNCTION_URL_INVOKE_STATEMENT_ID      = 'FunctionURLInvokeAllowPublicAccess'            # Second statement — lambda:InvokeFunction with InvokedViaFunctionUrl condition
FUNCTION_URL_INVOKE_ACTION            = 'lambda:InvokeFunction'
FUNCTION_URL_PRINCIPAL                = '*'


class Lambda__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def create_lambda(self, wait_for_active=False):                                     # Upsert — never deletes (preserves Function URL for CloudFront)
        with Duration(prefix='[create_lambda] | upsert:'):                              # No outer try/except: errors must propagate so CI surfaces the real failure
            lambda_function              = self.lambda_function()
            lambda_function.image_uri    = self.image_uri()
            lambda_function.architecture = LAMBDA_ARCHITECTURE
            lambda_function.memory_size  = LAMBDA_MEMORY_MB                             # osbot_aws reads memory_size (see create_kwargs → MemorySize)
            lambda_function.timeout      = LAMBDA_TIMEOUT_SECS

            self.set_lambda_env_vars(lambda_function)                                   # Propagate CI secrets → Lambda env

            if lambda_function.exists():
                with Duration(prefix='[create_lambda] | update image:'):
                    lambda_function.update_lambda_image_uri(self.image_uri())           # Rolls the function to the new image, URL host UUID unchanged
                with Duration(prefix='[create_lambda] | wait for image update:'):       # AWS rejects a second update while LastUpdateStatus=InProgress with ResourceConflictException
                    lambda_function.wait_for_function_update_to_complete(max_attempts=LAMBDA_UPDATE_MAX_ATTEMPTS, wait_time=LAMBDA_UPDATE_WAIT_SECS)
                with Duration(prefix='[create_lambda] | update configuration:'):
                    lambda_function.update_lambda_configuration()                       # Refresh env vars (Layers absent for Image pkgs → no-op on layers)
                with Duration(prefix='[create_lambda] | wait for config update:'):      # Same reason — subsequent function_url / add_permission calls need the function out of Pending
                    lambda_function.wait_for_function_update_to_complete(max_attempts=LAMBDA_UPDATE_MAX_ATTEMPTS, wait_time=LAMBDA_UPDATE_WAIT_SECS)
                create_result = {'status': 'ok', 'name': lambda_function.name, 'data': {'mode': 'update'}}
                pprint(create_result)
            else:
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

    def create_lambda_function_url(self):                                               # Preserve URL host UUID (CloudFront origin) — create if missing, never delete
        with Duration(prefix='[create_lambda_function_url] |'):
            lambda_function = self.lambda_function()
            function_name   = lambda_function.name

            if lambda_function.function_url_exists():                                   # 1. Keep the existing URL config intact — host UUID is the CloudFront origin
                url_policy         = {'status': 'kept', 'message': 'existing URL config preserved'}
                function_url_value = lambda_function.function_url()
                print(f'[create_lambda_function_url] step 1/3: preserved existing URL config -> {function_url_value}')
            else:
                url_result         = lambda_function.function_url_create_with_public_access(invoke_mode=FUNCTION_URL_INVOKE_MODE)    # First-time create: URL + statement 1 (lambda:InvokeFunctionUrl + StringEquals lambda:FunctionUrlAuthType=NONE)
                url_policy         = url_result.get('function_set_policy')
                function_url_value = url_result.get('function_url_create', {}).get('FunctionUrl')
                print(f'[create_lambda_function_url] step 1/3: created URL + InvokeFunctionUrl statement: {url_result}')

            boto3_client = boto3.client('lambda', region_name=get_env('AWS_DEFAULT_REGION'))                              # 2. & 3. Second statement via boto3 — osbot_aws.permission_add doesn't pass InvokedViaFunctionUrl

            try:                                                                                                          # 2. Remove stale statement (idempotent)
                boto3_client.remove_permission(FunctionName = function_name                  ,
                                                StatementId  = FUNCTION_URL_INVOKE_STATEMENT_ID)
                print('[create_lambda_function_url] step 2/3: removed stale InvokeFunction statement')
            except ClientError as error:
                if error.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                print('[create_lambda_function_url] step 2/3: no stale InvokeFunction statement')

            invoke_permission = boto3_client.add_permission(FunctionName           = function_name                  ,     # 3. Statement 2: lambda:InvokeFunction + Bool lambda:InvokedViaFunctionUrl=true
                                                             StatementId            = FUNCTION_URL_INVOKE_STATEMENT_ID,
                                                             Action                 = FUNCTION_URL_INVOKE_ACTION      ,
                                                             Principal              = FUNCTION_URL_PRINCIPAL          ,
                                                             InvokedViaFunctionUrl  = True                            )
            print(f'[create_lambda_function_url] step 3/3: added InvokeFunction statement: {invoke_permission.get("Statement")}')

            return dict(function_url      = function_url_value                          ,
                        auth_type         = FUNCTION_URL_AUTH_TYPE                      ,
                        url_policy        = url_policy                                 ,
                        invoke_permission = invoke_permission.get('Statement')         )

    def update_lambda_function(self):
        return self.lambda_function().update_lambda_image_uri(self.image_uri())

    def function_url(self):
        return self.lambda_function().function_url()
