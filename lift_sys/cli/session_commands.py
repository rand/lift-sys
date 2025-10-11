"""CLI commands for prompt session management.

Provides commands to create, list, inspect, and manage prompt refinement sessions.

Usage:
    uv run python -m lift_sys.cli session create --prompt "Your prompt here"
    uv run python -m lift_sys.cli session list
    uv run python -m lift_sys.cli session get SESSION_ID
    uv run python -m lift_sys.cli session resolve SESSION_ID HOLE_ID "resolution text"
    uv run python -m lift_sys.cli session finalize SESSION_ID
    uv run python -m lift_sys.cli session delete SESSION_ID
"""

from __future__ import annotations

import json
import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from lift_sys.client import SessionClient

app = typer.Typer(
    name="session",
    help="Manage prompt refinement sessions",
    no_args_is_help=True,
)
console = Console()


def get_client(api_url: str = "http://localhost:8000") -> SessionClient:
    """Get configured session client with automatic demo mode detection."""
    headers = {}

    # Auto-detect demo mode from environment variable
    if os.getenv("LIFT_SYS_ENABLE_DEMO_USER_HEADER") == "1":
        demo_user = os.getenv("LIFT_SYS_DEMO_USER", "cli-user")
        headers["x-demo-user"] = demo_user

    return SessionClient(base_url=api_url, headers=headers if headers else None)


@app.command("create")
def create_session(
    prompt: str | None = typer.Option(None, "--prompt", "-p", help="Natural language prompt"),
    ir_file: str | None = typer.Option(None, "--ir-file", "-i", help="Path to IR JSON file"),
    source: str = typer.Option(
        "prompt", "--source", "-s", help="Session source (prompt or reverse_mode)"
    ),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new prompt refinement session.

    Examples:
        # Create from prompt
        uv run python -m lift_sys.cli session create -p "A function that adds two numbers"

        # Create from IR file
        uv run python -m lift_sys.cli session create -i spec.json -s reverse_mode

        # Output as JSON for scripting
        uv run python -m lift_sys.cli session create -p "..." --json
    """
    if not prompt and not ir_file:
        console.print("[red]Error:[/red] Either --prompt or --ir-file must be provided")
        raise typer.Exit(1)

    client = get_client(api_url)
    ir_dict = None

    if ir_file:
        try:
            with open(ir_file) as f:
                ir_dict = json.load(f)
        except Exception as e:
            console.print(f"[red]Error reading IR file:[/red] {e}")
            raise typer.Exit(1)

    try:
        session = client.create_session(
            prompt=prompt,
            ir=ir_dict,
            source=source,
        )

        if output_json:
            print(
                json.dumps(
                    {
                        "session_id": session.session_id,
                        "status": session.status,
                        "source": session.source,
                        "ambiguities": session.ambiguities,
                    },
                    indent=2,
                )
            )
        else:
            console.print(
                Panel(
                    f"[green]✓ Session created[/green]\n\n"
                    f"ID: [cyan]{session.session_id}[/cyan]\n"
                    f"Status: {session.status}\n"
                    f"Source: {session.source}\n"
                    f"Ambiguities: {len(session.ambiguities)}",
                    title="Session Created",
                )
            )

            if session.ambiguities:
                console.print("\n[yellow]Unresolved holes:[/yellow]")
                for hole_id in session.ambiguities:
                    console.print(f"  • {hole_id}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_sessions(
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all active sessions.

    Example:
        uv run python -m lift_sys.cli session list
        uv run python -m lift_sys.cli session list --json
    """
    client = get_client(api_url)

    try:
        response = client.list_sessions()
        sessions = response.sessions

        if output_json:
            print(
                json.dumps(
                    [
                        {
                            "session_id": s.session_id,
                            "status": s.status,
                            "source": s.source,
                            "ambiguities_count": len(s.ambiguities),
                            "created_at": s.created_at,
                        }
                        for s in sessions
                    ],
                    indent=2,
                )
            )
        else:
            if not sessions:
                console.print("[yellow]No sessions found[/yellow]")
                return

            table = Table(title="Prompt Refinement Sessions")
            table.add_column("ID", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Source")
            table.add_column("Holes", justify="right")
            table.add_column("Created")

            for session in sessions:
                table.add_row(
                    session.session_id[:12] + "...",
                    session.status,
                    session.source,
                    str(len(session.ambiguities)),
                    session.created_at[:10],
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("get")
def get_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    show_ir: bool = typer.Option(False, "--show-ir", help="Include full IR in output"),
) -> None:
    """Get details of a specific session.

    Example:
        uv run python -m lift_sys.cli session get abc123...
        uv run python -m lift_sys.cli session get abc123... --show-ir --json
    """
    client = get_client(api_url)

    try:
        session = client.get_session(session_id)

        if output_json:
            data = {
                "session_id": session.session_id,
                "status": session.status,
                "source": session.source,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "ambiguities": session.ambiguities,
                "revision_count": session.revision_count,
            }
            if show_ir and session.current_draft:
                data["ir"] = session.current_draft.ir
                data["validation_status"] = session.current_draft.validation_status
            print(json.dumps(data, indent=2))
        else:
            lines = [
                f"[cyan]Session:[/cyan] {session.session_id}",
                f"[cyan]Status:[/cyan] {session.status}",
                f"[cyan]Source:[/cyan] {session.source}",
                f"[cyan]Created:[/cyan] {session.created_at}",
                f"[cyan]Updated:[/cyan] {session.updated_at}",
                f"[cyan]Revisions:[/cyan] {session.revision_count}",
            ]

            if session.current_draft:
                lines.extend(
                    [
                        f"[cyan]Draft Version:[/cyan] {session.current_draft.version}",
                        f"[cyan]Validation:[/cyan] {session.current_draft.validation_status}",
                    ]
                )

            lines.append(f"[cyan]Ambiguities:[/cyan] {len(session.ambiguities)}")

            console.print(Panel("\n".join(lines), title="Session Details"))

            if session.ambiguities:
                console.print("\n[yellow]Unresolved holes:[/yellow]")
                for hole_id in session.ambiguities:
                    console.print(f"  • {hole_id}")

            if show_ir and session.current_draft:
                console.print("\n[cyan]IR:[/cyan]")
                syntax = Syntax(
                    json.dumps(session.current_draft.ir, indent=2),
                    "json",
                    theme="monokai",
                )
                console.print(syntax)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("resolve")
def resolve_hole(
    session_id: str = typer.Argument(..., help="Session ID"),
    hole_id: str = typer.Argument(..., help="Hole ID to resolve"),
    resolution: str = typer.Argument(..., help="Resolution text"),
    resolution_type: str = typer.Option("clarify_intent", "--type", "-t", help="Resolution type"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Resolve a typed hole in a session.

    Example:
        uv run python -m lift_sys.cli session resolve abc123... hole_return_type "int"
    """
    client = get_client(api_url)

    try:
        session = client.resolve_hole(
            session_id=session_id,
            hole_id=hole_id,
            resolution_text=resolution,
            resolution_type=resolution_type,
        )

        if output_json:
            print(
                json.dumps(
                    {
                        "session_id": session.session_id,
                        "status": session.status,
                        "ambiguities": session.ambiguities,
                    },
                    indent=2,
                )
            )
        else:
            console.print(
                Panel(
                    f"[green]✓ Hole resolved[/green]\n\n"
                    f"Session: [cyan]{session.session_id[:12]}...[/cyan]\n"
                    f"Remaining holes: {len(session.ambiguities)}",
                    title="Resolution Applied",
                )
            )

            if session.ambiguities:
                console.print("\n[yellow]Remaining holes:[/yellow]")
                for h_id in session.ambiguities:
                    console.print(f"  • {h_id}")
            else:
                console.print("\n[green]✓ All holes resolved! Ready to finalize.[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("finalize")
def finalize_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_file: str | None = typer.Option(None, "--output", "-o", help="Save IR to file"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Finalize a session and get the completed IR.

    Example:
        uv run python -m lift_sys.cli session finalize abc123...
        uv run python -m lift_sys.cli session finalize abc123... -o finalized_ir.json
    """
    client = get_client(api_url)

    try:
        response = client.finalize_session(session_id)

        if output_file:
            with open(output_file, "w") as f:
                json.dump(response.ir, f, indent=2)
            console.print(f"[green]✓ IR saved to {output_file}[/green]")

        if output_json:
            print(json.dumps(response.ir, indent=2))
        else:
            console.print(
                Panel(
                    "[green]✓ Session finalized[/green]\n\nIR ready for code generation",
                    title="Finalization Complete",
                )
            )

            if not output_file:
                console.print("\n[cyan]IR Preview:[/cyan]")
                syntax = Syntax(
                    json.dumps(response.ir, indent=2),
                    "json",
                    theme="monokai",
                )
                console.print(syntax)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a session.

    Example:
        uv run python -m lift_sys.cli session delete abc123...
        uv run python -m lift_sys.cli session delete abc123... --yes
    """
    if not yes:
        confirm = typer.confirm(f"Delete session {session_id[:12]}...?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    client = get_client(api_url)

    try:
        client.delete_session(session_id)
        console.print(f"[green]✓ Session {session_id[:12]}... deleted[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("assists")
def get_assists(
    session_id: str = typer.Argument(..., help="Session ID"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get assist suggestions for resolving holes.

    Example:
        uv run python -m lift_sys.cli session assists abc123...
    """
    client = get_client(api_url)

    try:
        response = client.get_assists(session_id)

        if output_json:
            print(
                json.dumps(
                    [
                        {
                            "hole_id": a.hole_id,
                            "suggestions": a.suggestions,
                            "context": a.context,
                        }
                        for a in response.assists
                    ],
                    indent=2,
                )
            )
        else:
            if not response.assists:
                console.print("[yellow]No assists available[/yellow]")
                return

            console.print(f"\n[cyan]Assists for session {session_id[:12]}...[/cyan]\n")

            for assist in response.assists:
                console.print(f"[yellow]●[/yellow] [bold]{assist.hole_id}[/bold]")
                console.print(f"  Context: {assist.context}")
                if assist.suggestions:
                    console.print("  Suggestions:")
                    for suggestion in assist.suggestions:
                        console.print(f"    • {suggestion}")
                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
