"""Modal application bootstrap for lift-sys."""

from __future__ import annotations

import importlib
from typing import Any

from .infrastructure.deployment_settings import load_settings
from .infrastructure.modal_config import ModalAppConfig


def _import_modal() -> Any:
    """Import the Modal SDK lazily to keep local development lightweight."""

    return importlib.import_module("modal")


def create_modal_app(config: ModalAppConfig | None = None) -> Any:
    """Create the Modal app object and attach shared resources."""

    cfg = config or ModalAppConfig.from_env()
    settings = load_settings()
    modal = _import_modal()
    app = modal.App(cfg.app_name)
    # Resources such as volumes or dicts are referenced here to ensure Modal creates them.
    modal.Volume.from_name(
        cfg.model_volume.name, create_if_missing=cfg.model_volume.create_if_missing
    )
    modal.Dict.from_name(cfg.token_store_dict.name, create_if_missing=True)
    modal.Dict.from_name(cfg.user_preferences_dict.name, create_if_missing=True)
    # Surface the IaC scaling configuration to downstream modules.
    app.lift_sys_settings = settings
    return app
