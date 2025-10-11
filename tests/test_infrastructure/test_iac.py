"""Tests for the Modal IaC automation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from lift_sys.infrastructure import iac
from lift_sys.infrastructure.deployment_settings import load_settings


def test_build_deploy_command_default() -> None:
    command = iac.build_deploy_command()
    assert command == ["modal", "deploy", "lift_sys/modal_app.py"]


def test_build_deploy_command_with_force(tmp_path: Path) -> None:
    custom_app = tmp_path / "modal_app.py"
    command = iac.build_deploy_command(force=True, modal_app=custom_app)
    assert command == ["modal", "deploy", "--force", str(custom_app)]


def test_scale_updates_settings_and_applies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_path = tmp_path / "deployment_settings.json"
    calls: list[str] = []

    monkeypatch.setattr(iac, "update", lambda modal_app=None: calls.append("update"))

    result = iac.scale(
        api_replicas=3,
        vllm_concurrency=6,
        apply=True,
        settings_path=settings_path,
        modal_app=Path("lift_sys/modal_app.py"),
    )

    assert result.api.replicas == 3
    assert result.vllm.concurrency == 6
    assert calls == ["update"]

    persisted = load_settings(settings_path)
    assert persisted.api.replicas == 3
    assert persisted.vllm.concurrency == 6


def test_scale_skips_when_no_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(iac, "update", lambda modal_app=None: calls.append("update"))

    result = iac.scale(
        api_replicas=None,
        vllm_concurrency=None,
        apply=True,
        settings_path=tmp_path / "deployment_settings.json",
    )

    assert calls == []
    assert result.api.replicas == 1
    assert result.vllm.concurrency == 4


@pytest.mark.parametrize("api_replicas, vllm_concurrency", [(-1, None), (0, 5), (1, 0)])
def test_scale_rejects_invalid_values(api_replicas, vllm_concurrency) -> None:
    with pytest.raises(ValueError):
        iac.scale(api_replicas=api_replicas, vllm_concurrency=vllm_concurrency, apply=False)
