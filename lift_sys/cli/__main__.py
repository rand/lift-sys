"""CLI entry point for lift-sys."""

from __future__ import annotations

import typer

from .session_commands import app as session_app

# Create main CLI app
app = typer.Typer(
    name="lift-sys",
    help="Lift-sys command line interface",
    no_args_is_help=True,
)

# Add session commands
app.add_typer(session_app, name="session")


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
