"""Infrastructure-as-code automation helpers for Modal deployments."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .deployment_settings import DeploymentSettings, load_settings, save_settings


class ModalCliNotFoundError(RuntimeError):
    """Raised when the Modal CLI is not available on the system PATH."""


def _modal_cli_path() -> str:
    path = shutil.which("modal")
    if path is None:
        raise ModalCliNotFoundError(
            "Modal CLI not found. Install it from https://modal.com/docs/guide/cli and ensure it is on PATH."
        )
    return path


def build_deploy_command(force: bool = False, modal_app: Path | None = None) -> list[str]:
    """Construct the modal deploy command used for rollouts."""

    app_path = modal_app or Path("lift_sys/modal_app.py")
    command: list[str] = ["modal", "deploy"]
    if force:
        command.append("--force")
    command.append(str(app_path))
    return command


def run_modal_command(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """Execute a Modal CLI command, surfacing stderr/stdout to the caller."""

    cli_path = _modal_cli_path()
    command = list(args)
    if command and command[0] == "modal":
        command[0] = cli_path
    return subprocess.run(command, check=True, text=True, capture_output=False)


def deploy(modal_app: Path | None = None) -> None:
    """Deploy the Modal application using the pinned app definition."""

    command = build_deploy_command(force=False, modal_app=modal_app)
    run_modal_command(command)


def update(modal_app: Path | None = None) -> None:
    """Force a redeploy to pick up image or code updates."""

    command = build_deploy_command(force=True, modal_app=modal_app)
    run_modal_command(command)


def scale(
    *,
    api_replicas: int | None,
    vllm_concurrency: int | None,
    apply: bool,
    settings_path: Path | None = None,
    modal_app: Path | None = None,
) -> DeploymentSettings:
    """Update scaling parameters and optionally trigger an immediate redeploy."""

    settings = load_settings(settings_path)
    updated = False

    if api_replicas is not None:
        if api_replicas < 1:
            raise ValueError("api_replicas must be >= 1")
        settings.api.replicas = api_replicas
        updated = True

    if vllm_concurrency is not None:
        if vllm_concurrency < 1:
            raise ValueError("vllm_concurrency must be >= 1")
        settings.vllm.concurrency = vllm_concurrency
        updated = True

    if not updated:
        return settings

    save_settings(settings, settings_path)

    if apply:
        update(modal_app=modal_app)

    return settings


def cli(argv: Iterable[str] | None = None) -> None:
    """Entry point for `python -m lift_sys.infrastructure.iac`."""

    parser = argparse.ArgumentParser(description="lift-sys Modal IaC automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy", help="Deploy the Modal application")
    deploy_parser.set_defaults(func=lambda args: deploy())

    update_parser = subparsers.add_parser("update", help="Redeploy with the latest code and images")
    update_parser.set_defaults(func=lambda args: update())

    scale_parser = subparsers.add_parser("scale", help="Adjust worker counts and redeploy")
    scale_parser.add_argument(
        "--api-replicas", type=int, default=None, help="Number of API worker replicas"
    )
    scale_parser.add_argument(
        "--vllm-concurrency",
        type=int,
        default=None,
        help="Maximum concurrent vLLM generations",
    )
    scale_parser.add_argument(
        "--apply",
        action="store_true",
        help="Trigger a redeploy after writing the new scaling settings",
    )

    def _scale_handler(args: argparse.Namespace) -> None:
        try:
            scale(
                api_replicas=args.api_replicas,
                vllm_concurrency=args.vllm_concurrency,
                apply=args.apply,
            )
        except ValueError as exc:  # pragma: no cover - argparse handles exit
            scale_parser.error(str(exc))

    scale_parser.set_defaults(func=_scale_handler)

    args = parser.parse_args(tuple(argv) if argv is not None else None)
    args.func(args)


if __name__ == "__main__":
    cli()
