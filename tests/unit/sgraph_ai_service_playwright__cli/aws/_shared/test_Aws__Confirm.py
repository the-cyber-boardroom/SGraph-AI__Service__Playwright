# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Aws__Confirm
# ═══════════════════════════════════════════════════════════════════════════════

from unittest.mock import patch

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm import confirm_or_abort


class test_Aws__Confirm:

    def test_dry_run_returns_false_without_prompt(self):
        result = confirm_or_abort('delete it?', yes=False, dry_run=True)
        assert result is False

    def test_yes_returns_true_without_prompt(self):
        result = confirm_or_abort('delete it?', yes=True, dry_run=False)
        assert result is True

    def test_prompt_called_when_neither_yes_nor_dry_run(self):
        with patch('sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm.typer.confirm', return_value=True) as mock_confirm:
            result = confirm_or_abort('delete it?')
            mock_confirm.assert_called_once_with('delete it?', default=False)
            assert result is True
