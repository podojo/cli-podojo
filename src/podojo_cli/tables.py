from rich.console import Console
from rich.table import Table

# Off a terminal (Claude Code, a pipe) Rich falls back to 80 columns and cuts
# cells with "…", so agents end up guessing the rest of a batch ID. Tables
# render at their natural width up to this one instead.
OFF_TERMINAL_WIDTH = 200


def print_table(console: Console, table: Table) -> None:
    if not console.is_terminal:
        console = Console(width=OFF_TERMINAL_WIDTH)
    console.print(table)
