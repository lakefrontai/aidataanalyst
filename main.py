#!/usr/bin/env python3
"""
AI Data Analyst — CLI
Connects AWS Bedrock (Mistral AI) + Microsoft Fabric

Usage:
    python main.py
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from config import config
from bedrock_client import BedrockMistralClient
from fabric_client import FabricClient
from analyst import AnalystSession

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║      AI Data Analyst  •  Bedrock + Fabric        ║[/bold cyan]
[bold cyan]║   Mistral AI  ──►  Microsoft Fabric (T-SQL)      ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════╝[/bold cyan]
"""

HELP_TEXT = """
[bold]Commands:[/bold]
  [green]/tables[/green]          List all tables in the database
  [green]/schema[/green]          Show full database schema
  [green]/schema refresh[/green]  Reload schema from Fabric
  [green]/sample <table>[/green]  Show 3 sample rows from a table
  [green]/history[/green]         Show conversation history
  [green]/reset[/green]           Clear conversation history
  [green]/help[/green]            Show this help
  [green]/quit[/green]  or  [green]/exit[/green]  Exit

[bold]Data questions examples:[/bold]
  • "What are the top 10 customers by revenue this year?"
  • "Show me monthly sales trends for the last 6 months"
  • "Which products have declining sales vs last quarter?"
  • "What is the average order value by region?"
"""


def print_dataframe(df, title: str = "Results") -> None:
    """Render a DataFrame as a Rich table in the terminal."""
    if df is None or df.empty:
        console.print("[yellow]No data returned.[/yellow]")
        return

    table = Table(title=title, show_lines=True, header_style="bold magenta")
    for col in df.columns:
        table.add_column(str(col), overflow="fold")
    for _, row in df.iterrows():
        table.add_row(*[str(v) if v is not None else "NULL" for v in row])

    console.print(table)
    if df.attrs.get("truncated"):
        console.print(f"[yellow]Showing first {config.MAX_ROWS_DISPLAY} rows.[/yellow]")


def handle_command(cmd: str, session: AnalystSession, fabric: FabricClient) -> bool:
    """Handle /commands. Returns True if handled, False if it's a data question."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/quit", "/exit"):
        console.print("[bold red]Goodbye![/bold red]")
        sys.exit(0)

    elif command == "/help":
        console.print(HELP_TEXT)

    elif command == "/tables":
        with console.status("Fetching table list from Fabric…"):
            tables = fabric.list_tables()
        if tables:
            for t in tables:
                console.print(f"  • {t}")
        else:
            console.print("[yellow]No tables found.[/yellow]")

    elif command == "/schema":
        force = arg.strip().lower() == "refresh"
        with console.status("Loading schema…"):
            schema = session.load_schema(force=force)
        console.print(Panel(schema, title="Database Schema", border_style="blue"))

    elif command == "/sample":
        if not arg:
            console.print("[red]Usage: /sample <schema.table>[/red]")
        else:
            with console.status(f"Fetching sample rows from {arg}…"):
                df = fabric.get_sample(arg)
            print_dataframe(df, title=f"Sample: {arg}")

    elif command == "/history":
        for msg in session._history:
            role = msg["role"].upper()
            clr = "cyan" if role == "USER" else "green"
            console.print(f"[{clr}][{role}][/{clr}] {msg['content'][:200]}")

    elif command == "/reset":
        session.reset_history()
        console.print("[green]Conversation history cleared.[/green]")

    else:
        console.print(f"[red]Unknown command: {command}. Type /help for help.[/red]")

    return True


def run() -> None:
    """Main REPL entry point — connects Bedrock + Fabric and starts the CLI loop."""
    console.print(BANNER)

    # ── Validate config ───────────────────────────────────────────────────────
    errors = config.validate()
    if errors:
        console.print("[bold red]Configuration errors:[/bold red]")
        for e in errors:
            console.print(f"  ✗ {e}")
        console.print("\nCopy [bold].env.example[/bold] to [bold].env[/bold] and fill in your credentials.")
        sys.exit(1)

    # ── Connect ───────────────────────────────────────────────────────────────
    bedrock = BedrockMistralClient()
    fabric = FabricClient()

    console.print(f"[dim]Model:[/dim] {config.BEDROCK_MODEL_ID}")
    console.print(f"[dim]Fabric:[/dim] {config.FABRIC_SERVER} / {config.FABRIC_DATABASE}")

    with console.status("Connecting to Microsoft Fabric…"):
        try:
            fabric.connect()
        except Exception as e:
            console.print(f"[bold red]Fabric connection failed:[/bold red] {e}")
            sys.exit(1)

    console.print("[green]✓ Connected to Microsoft Fabric[/green]")

    with console.status("Loading schema…"):
        try:
            session = AnalystSession(fabric, bedrock)
            schema = session.load_schema()
            table_count = schema.count("Table:")
        except Exception as e:
            console.print(f"[bold red]Schema load failed:[/bold red] {e}")
            sys.exit(1)

    console.print(f"[green]✓ Schema loaded — {table_count} table(s) discovered[/green]")
    console.print("\nType a data question or [bold]/help[/bold] for commands.\n")

    # ── REPL ──────────────────────────────────────────────────────────────────
    try:
        while True:
            try:
                user_input = console.input("[bold cyan]You ▶[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[bold red]Interrupted. Goodbye![/bold red]")
                break

            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                handle_command(user_input, session, fabric)
                continue

            # Data question
            with console.status("[bold green]Thinking…[/bold green]"):
                result = session.ask(user_input)

            # Show generated SQL
            if result["sql"]:
                console.print(
                    Panel(
                        Syntax(result["sql"], "sql", theme="monokai", word_wrap=True),
                        title="[bold]Generated SQL[/bold]",
                        border_style="dim",
                    )
                )

            # Show tabular data
            if result["data"] is not None and not result["data"].empty:
                print_dataframe(result["data"], title="Query Results")

            # Show AI answer
            if result["answer"]:
                console.print(
                    Panel(
                        Markdown(result["answer"]),
                        title="[bold green]AI Analyst[/bold green]",
                        border_style="green",
                    )
                )

            console.print()

    finally:
        fabric.disconnect()
        console.print("[dim]Disconnected from Fabric.[/dim]")


if __name__ == "__main__":
    run()
