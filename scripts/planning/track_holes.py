#!/usr/bin/env python3
"""
Hole tracking and management utility.

Manages the hole inventory for the DSPy + Pydantic AI architecture proposal.
Supports querying, updating, and visualizing holes and their dependencies.

Usage:
    python track_holes.py list [--status STATUS] [--phase PHASE]
    python track_holes.py show HOLE_ID
    python track_holes.py ready [--phase PHASE]
    python track_holes.py resolve HOLE_ID --resolution PATH
    python track_holes.py phase-status PHASE
    python track_holes.py visualize [--output PATH]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Constants
REPO_ROOT = Path(__file__).parent.parent.parent
HOLE_INVENTORY_PATH = REPO_ROOT / "docs" / "planning" / "HOLE_INVENTORY.md"


class HoleStatus(str, Enum):
    """Status of a hole."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


class HoleType(str, Enum):
    """Type classification of a hole."""

    IMPLEMENTATION = "implementation"
    INTERFACE = "interface"
    SPECIFICATION = "specification"
    CONSTRAINT = "constraint"
    VALIDATION = "validation"


@dataclass
class Hole:
    """Represents a typed hole in the architecture."""

    id: str
    name: str
    type: HoleType
    kind: str  # Specific type (e.g., "DSPyProvider")
    status: HoleStatus
    description: str
    constraints: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    phase: int | None = None
    resolution_path: str | None = None

    @property
    def is_ready(self) -> bool:
        """Check if hole is ready to be worked on (no blockers)."""
        return self.status in (HoleStatus.PENDING, HoleStatus.READY) and not self.blocked_by


# Hole registry (from HOLE_INVENTORY.md)
HOLES = {
    "H1": Hole(
        id="H1",
        name="ProviderAdapter",
        type=HoleType.IMPLEMENTATION,
        kind="DSPyProvider",
        status=HoleStatus.BLOCKED,
        description="Integration layer between DSPy and Modal/SGLang providers",
        constraints=[
            "MUST preserve XGrammar constraints",
            "MUST support async execution",
            "MUST be compatible with DSPy.LM interface",
        ],
        blocks=["H8"],
        blocked_by=["H6"],
        phase=2,
    ),
    "H2": Hole(
        id="H2",
        name="StatePersistence",
        type=HoleType.IMPLEMENTATION,
        kind="GraphStateStore",
        status=HoleStatus.BLOCKED,
        description="Mechanism for persisting and restoring Pydantic AI graph state",
        constraints=[
            "MUST support round-trip serialization (no data loss)",
            "MUST handle Pydantic models",
            "MUST be atomic",
        ],
        blocks=["H11"],
        blocked_by=["H6"],
        phase=2,
    ),
    "H3": Hole(
        id="H3",
        name="CachingStrategy",
        type=HoleType.IMPLEMENTATION,
        kind="NodeCache",
        status=HoleStatus.BLOCKED,
        description="Caching mechanism for deterministic node outputs",
        constraints=[
            "MUST be deterministic",
            "MUST handle concurrent access",
            "MUST support invalidation",
        ],
        blocks=[],
        blocked_by=["H4"],
        phase=5,
    ),
    "H4": Hole(
        id="H4",
        name="ParallelizationImpl",
        type=HoleType.IMPLEMENTATION,
        kind="ParallelExecutor",
        status=HoleStatus.BLOCKED,
        description="Concurrent execution of independent graph nodes",
        constraints=[
            "MUST avoid race conditions",
            "MUST respect resource limits",
            "MUST be deterministic",
        ],
        blocks=["H3", "H16", "H18"],
        blocked_by=["H6"],
        phase=4,
    ),
    "H5": Hole(
        id="H5",
        name="ErrorRecovery",
        type=HoleType.IMPLEMENTATION,
        kind="ErrorHandler",
        status=HoleStatus.BLOCKED,
        description="Handling node failures and graph-level errors",
        constraints=[
            "MUST preserve graph state on failure",
            "MUST support retry with backoff",
        ],
        blocks=[],
        blocked_by=["H9"],
        phase=7,
    ),
    "H6": Hole(
        id="H6",
        name="NodeSignatureInterface",
        type=HoleType.INTERFACE,
        kind="Protocol",
        status=HoleStatus.READY,
        description="Contract between graph nodes and DSPy signatures",
        constraints=[
            "MUST be type-safe (generic over StateT)",
            "MUST support async execution",
            "MUST compose with Pydantic AI Graph",
        ],
        blocks=["H1", "H2", "H4", "H5"],
        blocked_by=[],
        phase=1,
    ),
    "H7": Hole(
        id="H7",
        name="TraceVisualizationProtocol",
        type=HoleType.INTERFACE,
        kind="Protocol",
        status=HoleStatus.BLOCKED,
        description="Interface for exposing graph execution traces to UI",
        constraints=[
            "MUST support real-time updates",
            "MUST include node inputs/outputs",
        ],
        blocks=[],
        blocked_by=["H11"],
        phase=5,
    ),
    "H8": Hole(
        id="H8",
        name="OptimizationAPI",
        type=HoleType.INTERFACE,
        kind="Protocol",
        status=HoleStatus.BLOCKED,
        description="Interface between pipeline and MIPROv2 optimizer",
        constraints=[
            "MUST support MIPROv2 and COPRO optimizers",
            "MUST accept custom metrics",
        ],
        blocks=[],
        blocked_by=["H10", "H1"],
        phase=3,
    ),
    "H9": Hole(
        id="H9",
        name="ValidationHooks",
        type=HoleType.INTERFACE,
        kind="Protocol",
        status=HoleStatus.READY,
        description="Pluggable validation at graph execution points",
        constraints=[
            "MUST be composable",
            "MUST support async execution",
        ],
        blocks=["H5"],
        blocked_by=[],
        phase=1,
    ),
    "H10": Hole(
        id="H10",
        name="OptimizationMetrics",
        type=HoleType.SPECIFICATION,
        kind="MetricDefinition",
        status=HoleStatus.BLOCKED,
        description="Exact metrics for evaluating pipeline quality",
        constraints=[
            "MUST be measurable",
            "MUST be differentiable or smooth",
            "MUST correlate with user satisfaction",
        ],
        blocks=["H8", "H17"],
        blocked_by=["H1"],
        phase=3,
    ),
    "H11": Hole(
        id="H11",
        name="ExecutionHistorySchema",
        type=HoleType.SPECIFICATION,
        kind="DatabaseSchema",
        status=HoleStatus.BLOCKED,
        description="Database schema for storing graph execution traces",
        constraints=[
            "MUST support replay",
            "MUST store node inputs/outputs",
        ],
        blocks=["H7"],
        blocked_by=["H2"],
        phase=2,
    ),
    "H12": Hole(
        id="H12",
        name="ConfidenceCalibration",
        type=HoleType.SPECIFICATION,
        kind="ScoringFunction",
        status=HoleStatus.BLOCKED,
        description="Method for scoring hole suggestion confidence",
        constraints=[
            "MUST correlate with actual accuracy",
            "MUST be calibrated",
        ],
        blocks=[],
        blocked_by=["H10"],
        phase=3,
    ),
    "H13": Hole(
        id="H13",
        name="FeatureFlagSchema",
        type=HoleType.SPECIFICATION,
        kind="ConfigurationSchema",
        status=HoleStatus.BLOCKED,
        description="Configuration for gradual rollout and A/B testing",
        constraints=[
            "MUST support user-level flags",
            "MUST support percentage rollout",
        ],
        blocks=[],
        blocked_by=["H15"],
        phase=6,
    ),
    "H14": Hole(
        id="H14",
        name="ResourceLimits",
        type=HoleType.CONSTRAINT,
        kind="ResourceSpecification",
        status=HoleStatus.READY,
        description="Memory, CPU, and concurrency limits for graph execution",
        constraints=[
            "MUST fit within Modal resource limits",
            "MUST leave headroom for system overhead",
        ],
        blocks=["H16"],
        blocked_by=[],
        phase=1,
    ),
    "H15": Hole(
        id="H15",
        name="MigrationConstraints",
        type=HoleType.CONSTRAINT,
        kind="CompatibilityRequirement",
        status=HoleStatus.BLOCKED,
        description="Requirements for backward compatibility with existing sessions",
        constraints=[
            "MUST preserve all session data",
            "MUST allow resuming old sessions",
        ],
        blocks=["H13", "H19"],
        blocked_by=["H2"],
        phase=6,
    ),
    "H16": Hole(
        id="H16",
        name="ConcurrencyModel",
        type=HoleType.CONSTRAINT,
        kind="ConcurrencySpecification",
        status=HoleStatus.BLOCKED,
        description="Maximum concurrent operations given provider limits",
        constraints=[
            "MUST respect provider rate limits",
            "MUST account for graph parallelization",
        ],
        blocks=["H4"],
        blocked_by=["H14"],
        phase=4,
    ),
    "H17": Hole(
        id="H17",
        name="OptimizationValidation",
        type=HoleType.VALIDATION,
        kind="StatisticalTest",
        status=HoleStatus.BLOCKED,
        description="Statistical validation that optimization improves performance",
        constraints=[
            "MUST use statistical significance (p < 0.05)",
            "MUST measure effect size",
        ],
        blocks=[],
        blocked_by=["H10"],
        phase=7,
    ),
    "H18": Hole(
        id="H18",
        name="ConcurrencyValidation",
        type=HoleType.VALIDATION,
        kind="DeterminismTest",
        status=HoleStatus.BLOCKED,
        description="Validation that parallel execution is deterministic and safe",
        constraints=[
            "MUST run many iterations (≥100)",
            "MUST check for race conditions",
        ],
        blocks=[],
        blocked_by=["H4"],
        phase=4,
    ),
    "H19": Hole(
        id="H19",
        name="BackwardCompatTest",
        type=HoleType.VALIDATION,
        kind="MigrationTest",
        status=HoleStatus.BLOCKED,
        description="Test suite validating session migration correctness",
        constraints=[
            "MUST test on real production sessions",
            "MUST verify no data loss",
        ],
        blocks=[],
        blocked_by=["H15"],
        phase=6,
    ),
}


def list_holes(status: HoleStatus | None = None, phase: int | None = None) -> list[Hole]:
    """List holes filtered by status and/or phase."""
    holes = list(HOLES.values())

    if status:
        holes = [h for h in holes if h.status == status]

    if phase:
        holes = [h for h in holes if h.phase == phase]

    return holes


def show_hole(hole_id: str) -> None:
    """Show detailed information about a hole."""
    hole = HOLES.get(hole_id.upper())
    if not hole:
        print(f"Error: Hole {hole_id} not found")
        return

    print(f"\n{'=' * 60}")
    print(f"{hole.id}: {hole.name}")
    print(f"{'=' * 60}\n")

    print(f"Type:        {hole.type.value}")
    print(f"Kind:        {hole.kind}")
    print(f"Status:      {hole.status.value}")
    print(f"Phase:       {hole.phase}")
    print(f"Ready:       {'✅ Yes' if hole.is_ready else '❌ No'}\n")

    print(f"Description: {hole.description}\n")

    print("Constraints:")
    for constraint in hole.constraints:
        print(f"  - {constraint}")

    print("\nDependencies:")
    print(f"  Blocks:     {', '.join(hole.blocks) if hole.blocks else 'None'}")
    print(f"  Blocked by: {', '.join(hole.blocked_by) if hole.blocked_by else 'None'}")

    if hole.resolution_path:
        print(f"\nResolution:  {hole.resolution_path}")

    print()


def ready_holes(phase: int | None = None) -> list[Hole]:
    """Get holes that are ready to be worked on."""
    holes = [h for h in HOLES.values() if h.is_ready]

    if phase:
        holes = [h for h in holes if h.phase == phase]

    return holes


def resolve_hole(hole_id: str, resolution_path: str) -> None:
    """Mark a hole as resolved with resolution path."""
    hole = HOLES.get(hole_id.upper())
    if not hole:
        print(f"Error: Hole {hole_id} not found")
        return

    hole.status = HoleStatus.RESOLVED
    hole.resolution_path = resolution_path

    print(f"✅ Marked {hole.id} as RESOLVED")
    print(f"   Resolution: {resolution_path}")

    # Show newly unblocked holes
    newly_ready = []
    for other_hole in HOLES.values():
        if hole.id in other_hole.blocked_by:
            # Remove this hole from blockers
            other_hole.blocked_by.remove(hole.id)
            # Check if now ready
            if other_hole.is_ready and other_hole.status != HoleStatus.RESOLVED:
                newly_ready.append(other_hole)
                other_hole.status = HoleStatus.READY

    if newly_ready:
        print("\n🎯 Newly unblocked holes:")
        for h in newly_ready:
            print(f"   - {h.id}: {h.name}")


def phase_status(phase: int) -> None:
    """Show status of all holes in a phase."""
    holes = [h for h in HOLES.values() if h.phase == phase]

    if not holes:
        print(f"No holes found for Phase {phase}")
        return

    print(f"\n{'=' * 60}")
    print(f"Phase {phase} Status")
    print(f"{'=' * 60}\n")

    total = len(holes)
    resolved = sum(1 for h in holes if h.status == HoleStatus.RESOLVED)
    ready = sum(1 for h in holes if h.is_ready and h.status != HoleStatus.RESOLVED)
    blocked = sum(1 for h in holes if h.blocked_by and h.status != HoleStatus.RESOLVED)

    print(f"Total holes:    {total}")
    print(f"Resolved:       {resolved} ({resolved / total * 100:.0f}%)")
    print(f"Ready to work:  {ready}")
    print(f"Blocked:        {blocked}\n")

    # Group by status
    by_status: dict[HoleStatus, list[Hole]] = {}
    for hole in holes:
        by_status.setdefault(hole.status, []).append(hole)

    for status in [
        HoleStatus.RESOLVED,
        HoleStatus.READY,
        HoleStatus.IN_PROGRESS,
        HoleStatus.BLOCKED,
        HoleStatus.PENDING,
    ]:
        if status in by_status:
            print(f"{status.value.upper()}:")
            for hole in by_status[status]:
                print(f"  {hole.id}: {hole.name}")
            print()


def visualize_dependencies(output_path: Path | None = None) -> None:
    """Generate dependency graph visualization (DOT format)."""
    dot = ["digraph HoleDependencies {"]
    dot.append("  rankdir=LR;")
    dot.append("  node [shape=box, style=rounded];")

    # Color by status
    status_colors = {
        HoleStatus.RESOLVED: "green",
        HoleStatus.READY: "lightblue",
        HoleStatus.IN_PROGRESS: "yellow",
        HoleStatus.BLOCKED: "gray",
        HoleStatus.PENDING: "white",
    }

    # Add nodes
    for hole in HOLES.values():
        color = status_colors.get(hole.status, "white")
        label = f"{hole.id}\\n{hole.name}"
        dot.append(f'  {hole.id} [label="{label}", fillcolor={color}, style="filled,rounded"];')

    # Add edges (dependencies)
    for hole in HOLES.values():
        for blocker in hole.blocked_by:
            dot.append(f"  {blocker} -> {hole.id};")

    dot.append("}")

    dot_content = "\n".join(dot)

    if output_path:
        output_path.write_text(dot_content)
        print(f"✅ Dependency graph written to {output_path}")
        print("   Use 'dot -Tpng {file} -o output.png' to generate image")
    else:
        print(dot_content)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Track and manage architecture holes")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List holes")
    list_parser.add_argument("--status", type=str, help="Filter by status")
    list_parser.add_argument("--phase", type=int, help="Filter by phase")

    # show command
    show_parser = subparsers.add_parser("show", help="Show hole details")
    show_parser.add_argument("hole_id", type=str, help="Hole ID (e.g., H6)")

    # ready command
    ready_parser = subparsers.add_parser("ready", help="Show ready holes")
    ready_parser.add_argument("--phase", type=int, help="Filter by phase")

    # resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Mark hole as resolved")
    resolve_parser.add_argument("hole_id", type=str, help="Hole ID")
    resolve_parser.add_argument("--resolution", type=str, required=True, help="Path to resolution")

    # phase-status command
    phase_parser = subparsers.add_parser("phase-status", help="Show phase status")
    phase_parser.add_argument("phase", type=int, help="Phase number")

    # visualize command
    viz_parser = subparsers.add_parser("visualize", help="Generate dependency graph")
    viz_parser.add_argument("--output", type=str, help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "list":
        status = HoleStatus(args.status) if args.status else None
        holes = list_holes(status=status, phase=args.phase)

        print(f"\nFound {len(holes)} hole(s):\n")
        for hole in holes:
            status_icon = (
                "✅" if hole.status == HoleStatus.RESOLVED else ("🎯" if hole.is_ready else "⏳")
            )
            print(f"{status_icon} {hole.id}: {hole.name} ({hole.status.value})")

    elif args.command == "show":
        show_hole(args.hole_id)

    elif args.command == "ready":
        holes = ready_holes(phase=args.phase)

        if not holes:
            print("No holes currently ready to work on.")
        else:
            print(f"\n🎯 {len(holes)} hole(s) ready to work on:\n")
            for hole in holes:
                print(f"  {hole.id}: {hole.name} (Phase {hole.phase})")

    elif args.command == "resolve":
        resolve_hole(args.hole_id, args.resolution)

    elif args.command == "phase-status":
        phase_status(args.phase)

    elif args.command == "visualize":
        output = Path(args.output) if args.output else None
        visualize_dependencies(output)


if __name__ == "__main__":
    main()
