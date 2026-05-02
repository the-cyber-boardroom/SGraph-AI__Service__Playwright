# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — CLI entry point
# Run: python scripts/sg_compute.py <verb> <args>
# Future: installed as `sg-compute` console_script via pyproject.toml
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute.cli.Cli__Compute import app

if __name__ == '__main__':
    app()
