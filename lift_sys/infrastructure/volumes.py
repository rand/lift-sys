"""Persistent storage definitions for Modal volumes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .modal_config import ModalVolumeRef


@dataclass(slots=True)
class VolumeSpec:
    """Declarative representation of a Modal volume."""

    ref: ModalVolumeRef
    mount_path: str


def default_model_volume() -> VolumeSpec:
    """Volume used to store model weights shared between deployments."""

    return VolumeSpec(ref=ModalVolumeRef("lift-sys-models"), mount_path="/models")


def iter_all_volumes() -> Iterable[VolumeSpec]:
    """Yield all statically known volume definitions."""

    yield default_model_volume()
