"""IR package exports."""

from .differ import (
    CategoryComparison,
    ComparisonResult,
    DiffCategory,
    DiffKind,
    DiffSeverity,
    IRComparer,
    IRDiff,
)
from .merger import (
    ConflictResolution,
    IRMerger,
    MergeConflict,
    MergeResult,
    MergeStrategy,
)
from .models import *  # noqa: F401,F403
from .parser import IRParser, ParserConfig
from .versioning import IRVersion, VersionedIR, VersionMetadata

__all__ = [
    "IRParser",
    "ParserConfig",
    "IRComparer",
    "DiffCategory",
    "DiffKind",
    "DiffSeverity",
    "IRDiff",
    "CategoryComparison",
    "ComparisonResult",
    "IRMerger",
    "MergeStrategy",
    "MergeResult",
    "MergeConflict",
    "ConflictResolution",
    "VersionMetadata",
    "IRVersion",
    "VersionedIR",
] + [name for name in globals() if name[0].isupper()]
