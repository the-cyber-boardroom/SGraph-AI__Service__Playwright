# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge__Bench
# Typer app for `sg edge bench` — doc-05 measurement harness.
#
#   scenario     run one scenario id (P-01, F-01, X-05, …)  [Slice 6]
#   primitives   run all P-* scenarios                       [Slice 6]
#   flows        run all flow scenarios                      [Slice 6]
#   failures     run all failure scenarios                   [Slice 6]
#   full         run the full suite                          [Slice 6]
#
# The measurement engine (Edge_Bench__Runner / Edge_Bench__Stats) is live now;
# the scenario bodies (P-*/F-*/X-*) and target wiring are Slice 6.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console

app = typer.Typer(name='bench', help='SG/Edge bench harness (doc-05).', no_args_is_help=True)

_SLICE6 = '\n  [dim]⌛  Scenario bodies are Slice 6 (docker-compose stack + live target wiring)[/]\n'


@app.command(name='scenario', help='Run one bench scenario by ID (P-01, F-01, X-05, …) [Slice 6].')
def scenario(scenario_id: str = typer.Argument(..., metavar='SCENARIO_ID', help='Scenario ID e.g. P-01')):
    Console(highlight=False).print(_SLICE6)


@app.command(name='primitives', help='Run all primitive scenarios (P-*) [Slice 6].')
def primitives():
    Console(highlight=False).print(_SLICE6)


@app.command(name='flows', help='Run all flow scenarios [Slice 6].')
def flows():
    Console(highlight=False).print(_SLICE6)


@app.command(name='failures', help='Run all failure scenarios [Slice 6].')
def failures():
    Console(highlight=False).print(_SLICE6)


@app.command(name='full', help='Run the full bench suite (primitives + flows + failures) [Slice 6].')
def full():
    Console(highlight=False).print(_SLICE6)
