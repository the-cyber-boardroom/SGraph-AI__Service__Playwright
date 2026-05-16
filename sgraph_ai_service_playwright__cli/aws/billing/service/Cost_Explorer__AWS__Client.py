# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cost_Explorer__AWS__Client
# Sole boto3 boundary for AWS Cost Explorer (ce) and STS operations in the
# billing sub-package. Follows the same isolation precedent as
# ACM__AWS__Client and Route53__AWS__Client — one import boundary, one seam
# method (client()) that tests can override.
#
# FOLLOW-UP: osbot-aws has no Cost Explorer wrapper at the time of writing.
# Once one lands, replace the raw boto3 calls here and remove the EXCEPTION
# note. The STS call (get_caller_account_id) lives here too because the
# billing sub-package needs account provenance and STS is tightly coupled to
# the same credential context.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                          # EXCEPTION — see module header
import botocore.exceptions

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Cost_Explorer__AWS__Client(Type_Safe):                                         # Isolated boto3 boundary for Cost Explorer read operations

    def client(self):                                                                  # Single seam — tests override to return a fake client
        return boto3.client('ce')

    def get_cost_and_usage(self, start: str, end: str,
                           granularity: str = 'DAILY',
                           metrics: list = None,
                           group_by: list = None,
                           record_types: list = None) -> list:                       # Calls ce.get_cost_and_usage, paginates via NextPageToken, returns raw ResultsByTime list
        if metrics is None:
            metrics = ['UnblendedCost']
        if group_by is None:
            group_by = []
        if record_types is None:
            record_types = ['Usage']                                                  # Default: Usage only — matches Cost Explorer console default and excludes credits/refunds/taxes

        ce       = self.client()
        params   = dict(TimePeriod   = dict(Start=start, End=end),
                        Granularity  = granularity               ,
                        Metrics      = metrics                   )
        if group_by:
            params['GroupBy'] = group_by
        if record_types:                                                               # Empty list means no filter — include all charge types (credits, refunds, taxes, …)
            params['Filter'] = {'Dimensions': {'Key': 'RECORD_TYPE',
                                               'Values': record_types,
                                               'MatchOptions': ['EQUALS']}}

        results = []
        try:
            while True:
                resp = ce.get_cost_and_usage(**params)
                results.extend(resp.get('ResultsByTime', []))
                next_token = resp.get('NextPageToken')
                if not next_token:
                    break
                params['NextPageToken'] = next_token
        except botocore.exceptions.ClientError as e:
            code = e.response['Error']['Code']
            msg  = e.response['Error'].get('Message', '')
            if code == 'DataUnavailableException':                                       # Cost Explorer disabled on the account or first-24h data prep window
                account_id = self._safe_account_id()
                raise RuntimeError(
                    f'Error: AWS Cost Explorer is not enabled for account {account_id}.\n'
                    f'\n'
                    f'Cost Explorer must be enabled once per account from the AWS Console:\n'
                    f'  https://console.aws.amazon.com/cost-management/home#/cost-explorer\n'
                    f'\n'
                    f'After enabling, the first API call may fail for up to 24 hours while AWS\n'
                    f'prepares the data. Re-run `sg aws billing <verb>` once that window has passed.'
                ) from e
            if code in ('AccessDeniedException', 'AccessDenied', 'UnauthorizedException'):  # IAM principal missing ce:GetCostAndUsage — Cost Explorer itself may be enabled
                account_id = self._safe_account_id()
                raise RuntimeError(
                    f'Error: AWS principal is not authorised to call Cost Explorer in account {account_id}.\n'
                    f'\n'
                    f'AWS reported: {code}: {msg}\n'
                    f'\n'
                    f'Cost Explorer may already be enabled (the AWS Console can show spend even\n'
                    f"when the API can't), but the IAM identity these CLI credentials resolve to\n"
                    f'lacks the required permissions. Attach a policy granting:\n'
                    f'\n'
                    f'    ce:GetCostAndUsage\n'
                    f'    ce:GetDimensionValues   (optional, for future group-by surfaces)\n'
                    f'    sts:GetCallerIdentity   (already required and presumably present)\n'
                    f'\n'
                    f'on Resource "*" — Cost Explorer does not support resource-level IAM.\n'
                    f'\n'
                    f'Check which principal is being used:\n'
                    f'    aws sts get-caller-identity\n'
                    f'\n'
                    f'Then attach the policy to that user/role in IAM (or switch to a profile\n'
                    f'whose principal already has it).'
                ) from e
            raise

        self._check_currency(results, metrics[0] if metrics else 'UnblendedCost')   # Validate all amounts are USD

        return results

    def _check_currency(self, results: list, metric: str):                           # Raise if any returned amount is not USD
        for result in results:
            for group in result.get('Groups', []):
                unit = group.get('Metrics', {}).get(metric, {}).get('Unit', 'USD')
                if unit != 'USD':
                    account_id = self._safe_account_id()
                    raise RuntimeError(
                        f"Error: AWS Cost Explorer returned non-USD currency unit '{unit}' for account\n"
                        f'{account_id}. This CLI hard-codes USD output; multi-currency rendering is\n'
                        f"out of scope for MVP. File an issue if you need {unit} support."
                    )
            total_metrics = result.get('Total', {})
            for metric_name, metric_data in total_metrics.items():
                unit = metric_data.get('Unit', 'USD')
                if unit != 'USD':
                    account_id = self._safe_account_id()
                    raise RuntimeError(
                        f"Error: AWS Cost Explorer returned non-USD currency unit '{unit}' for account\n"
                        f'{account_id}. This CLI hard-codes USD output; multi-currency rendering is\n'
                        f"out of scope for MVP. File an issue if you need {unit} support."
                    )

    def get_caller_account_id(self) -> str:                                           # Uses STS get_caller_identity — same boto3 credential context as Cost Explorer
        sts = boto3.client('sts')
        return sts.get_caller_identity()['Account']

    def _safe_account_id(self) -> str:                                                # Best-effort account id for error messages; falls back to '<unknown>' on failure
        try:
            return self.get_caller_account_id()
        except Exception:
            return '<unknown>'
