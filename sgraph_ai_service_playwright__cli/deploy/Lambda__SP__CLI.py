# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lambda__SP__CLI
# Creates (or updates-in-place) the SP CLI Lambda from the ECR image and wires
# up a public Function URL for HTTP access.
#
# Tuning
# ──────
#   memory_size  = 1024 MB   — Ample for an adapter Lambda; the heavy lifting
#                              is AWS API calls, not in-process compute.
#   timeout      = 120 s     — sp create takes ~60s end-to-end (RunInstances
#                              + wait_for_instance_running). Buffer to 120s
#                              so API Gateway-style callers get a clean
#                              timeout rather than a hung invocation.
#   architecture = x86_64    — Matches the base image published tag.
#
# Auth: AuthType=NONE on the Function URL (matching the Playwright service
# pattern). The FastAPI app's X-API-Key middleware gates the routes — don't
# remove the API key env vars from set_env_vars() unless you know what you're
# doing.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3
from botocore.exceptions                                                            import ClientError

from osbot_aws.deploy.Deploy_Lambda                                                 import Deploy_Lambda
from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.utils.Env                                                          import get_env


APP_NAME                         = 'sp-playwright-cli'
DEFAULT_STAGE                    = 'dev'

LAMBDA_MEMORY_MB                 = 1024                                             # Adapter-sized; AWS API calls don't need Playwright's 5120MB
LAMBDA_TIMEOUT_SECS              = 120                                              # sp create takes ~60s; buffer 2x
LAMBDA_ARCHITECTURE              = 'x86_64'                                         # Matches public.ecr.aws/lambda/python:3.12
LAMBDA_HANDLER                   = 'sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler'

LAMBDA_UPDATE_MAX_ATTEMPTS       = 200                                              # 200 × 0.5s = 100s — smaller image than Playwright, but keep headroom
LAMBDA_UPDATE_WAIT_SECS          = 0.5

FUNCTION_URL_INVOKE_MODE         = 'BUFFERED'
FUNCTION_URL_AUTH_TYPE           = 'NONE'                                           # API-key middleware enforces access inside the app
FUNCTION_URL_INVOKE_STATEMENT_ID = 'FunctionURLInvokeAllowPublicAccess'
FUNCTION_URL_INVOKE_ACTION       = 'lambda:InvokeFunction'
FUNCTION_URL_PRINCIPAL           = '*'


class Lambda__SP__CLI(Type_Safe):
    stage    : str = DEFAULT_STAGE
    role_arn : str                                                                  # Required — set by the provisioner after SP__CLI__Lambda__Role.ensure()
    image_uri: str                                                                  # Required — set by the provisioner after Docker__SP__CLI.build_and_push()

    def lambda_name(self) -> str:                                                   # e.g. sp-playwright-cli-dev
        return f'{APP_NAME}-{self.stage}'

    def upsert(self, wait_for_active: bool = True) -> dict:                         # Idempotent — never deletes; preserves Function URL host UUID
        deploy_lambda                  = Deploy_Lambda(handler=LAMBDA_HANDLER, lambda_name=self.lambda_name())   # Deploy_Lambda accepts the handler path as a string; passing None blows up on `handler.__module__`. The actual handler resolution for container-image Lambdas comes from the Dockerfile CMD; this string is informational on the Python side.
        lambda_function                = deploy_lambda.lambda_function()
        lambda_function.image_uri      = self.image_uri
        lambda_function.architecture   = LAMBDA_ARCHITECTURE
        lambda_function.memory_size    = LAMBDA_MEMORY_MB
        lambda_function.timeout        = LAMBDA_TIMEOUT_SECS
        lambda_function.role           = self.role_arn

        self.set_env_vars(lambda_function)

        if lambda_function.exists():
            lambda_function.update_lambda_image_uri(self.image_uri)
            lambda_function.wait_for_function_update_to_complete(max_attempts=LAMBDA_UPDATE_MAX_ATTEMPTS, wait_time=LAMBDA_UPDATE_WAIT_SECS)
            lambda_function.update_lambda_configuration()
            lambda_function.wait_for_function_update_to_complete(max_attempts=LAMBDA_UPDATE_MAX_ATTEMPTS, wait_time=LAMBDA_UPDATE_WAIT_SECS)
            create_result = {'status': 'ok', 'name': lambda_function.name, 'data': {'mode': 'update'}}
        else:
            create_result = lambda_function.create()

        if wait_for_active:
            lambda_function.wait_for_state_active(max_wait_count=80)

        function_url = self.create_function_url(lambda_function)
        return {'create_result': create_result,
                'function_url' : function_url,
                'lambda_name'  : self.lambda_name()}

    def set_env_vars(self, lambda_function) -> None:
        env_vars = {'FAST_API__AUTH__API_KEY__NAME'  : get_env('FAST_API__AUTH__API_KEY__NAME'  ) or 'X-API-Key',   # Middleware rejects all requests without these; default NAME keeps the CLI + service in sync
                    'FAST_API__AUTH__API_KEY__VALUE' : get_env('FAST_API__AUTH__API_KEY__VALUE' ),
                    'AWS_DEFAULT_REGION'             : get_env('AWS_DEFAULT_REGION'             )}
        for key, value in env_vars.items():
            if value:
                lambda_function.set_env_variable(key, value)

    def create_function_url(self, lambda_function) -> dict:                         # Two-statement pattern required for AuthType=NONE URLs created after Oct 2025
        if lambda_function.function_url_exists():
            function_url_value = lambda_function.function_url()
            url_status         = 'preserved'
        else:
            url_result         = lambda_function.function_url_create_with_public_access(invoke_mode=FUNCTION_URL_INVOKE_MODE)
            function_url_value = url_result.get('function_url_create', {}).get('FunctionUrl')
            url_status         = 'created'

        boto3_client = boto3.client('lambda', region_name=get_env('AWS_DEFAULT_REGION'))
        try:                                                                        # Statement 2 of 2 — InvokeFunction with InvokedViaFunctionUrl; remove stale first so re-runs don't accumulate
            boto3_client.remove_permission(FunctionName=self.lambda_name(), StatementId=FUNCTION_URL_INVOKE_STATEMENT_ID)
        except ClientError as error:
            if error.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        boto3_client.add_permission(FunctionName          = self.lambda_name()           ,
                                    StatementId           = FUNCTION_URL_INVOKE_STATEMENT_ID,
                                    Action                = FUNCTION_URL_INVOKE_ACTION      ,
                                    Principal             = FUNCTION_URL_PRINCIPAL          ,
                                    InvokedViaFunctionUrl = True                            )
        return {'function_url': function_url_value, 'auth_type': FUNCTION_URL_AUTH_TYPE, 'status': url_status}
