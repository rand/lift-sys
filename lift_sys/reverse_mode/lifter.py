"""Reverse mode lifting of specifications from existing code."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from ..ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
    TypedHole,
)
from .analyzers import CodeQLAnalyzer, DaikonAnalyzer, Finding
from .stack_graphs import StackGraphAnalyzer


class LifterError(Exception):
    """Base exception for all lifter errors."""

    pass


class RepositoryNotLoadedError(LifterError):
    """Repository must be loaded before analysis."""

    pass


class AnalysisTimeoutError(LifterError):
    """Analysis exceeded time limit."""

    def __init__(self, file_path: str, timeout_seconds: float):
        self.file_path = file_path
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Analysis of {file_path} timed out after {timeout_seconds}s")


class TotalTimeLimitExceededError(LifterError):
    """Total analysis time exceeded configured limit."""

    def __init__(self, elapsed: float, limit: float, files_analyzed: int, total_files: int):
        self.elapsed = elapsed
        self.limit = limit
        self.files_analyzed = files_analyzed
        self.total_files = total_files
        super().__init__(
            f"Total time limit exceeded ({elapsed:.1f}s > {limit}s) after analyzing "
            f"{files_analyzed}/{total_files} files"
        )


class AnalysisError(LifterError):
    """Error during file analysis."""

    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(
            f"Failed to analyze {file_path}: {type(original_error).__name__}: {original_error}"
        )


class FileTooLargeError(LifterError):
    """File exceeds size limit."""

    def __init__(self, file_path: str, size_mb: float, limit_mb: float):
        self.file_path = file_path
        self.size_mb = size_mb
        self.limit_mb = limit_mb
        super().__init__(f"File {file_path} is too large ({size_mb:.1f}MB > {limit_mb}MB limit)")


@dataclass
class LifterConfig:
    # Analysis tool configuration
    codeql_queries: Iterable[str] = field(default_factory=lambda: ["security/default"])
    daikon_entrypoint: str = "main"
    stack_index_path: str | None = None
    run_codeql: bool = True
    run_daikon: bool = True
    run_stack_graphs: bool = True

    # Resource limits
    max_files: int | None = None  # Maximum number of files to analyze (None = no limit)
    max_file_size_mb: float = 10.0  # Maximum file size in MB (default: 10MB)
    timeout_per_file_seconds: float | None = None  # Timeout per file analysis (None = no limit)
    max_total_time_seconds: float | None = None  # Maximum total analysis time (None = no limit)

    # Causal analysis configuration (Week 4: H20-H22 integration)
    run_causal: bool = (
        False  # Enable causal analysis (default: disabled for backward compatibility)
    )
    causal_mode: str = "auto"  # Causal analysis mode: "auto", "static", or "dynamic"
    causal_collect_traces: bool = False  # Collect execution traces for dynamic mode
    causal_num_traces: int = 200  # Number of execution traces to collect
    causal_enable_circuit_breaker: bool = True  # Enable circuit breaker for repeated failures
    causal_circuit_breaker_threshold: int = 3  # Circuit breaker failure threshold


@dataclass
class RepositoryHandle:
    identifier: str
    workspace_path: Path | None = None
    archive_path: Path | None = None
    branch: str | None = None


class SpecificationLifter:
    def __init__(self, config: LifterConfig, repo: Repo | None = None) -> None:
        self.config = config
        self.repo = repo
        self.codeql = CodeQLAnalyzer()
        self.daikon = DaikonAnalyzer()
        self.stack_graphs = StackGraphAnalyzer()
        self.progress_log: list[str] = []

        # Initialize causal analysis components if enabled
        self.causal_enhancer = None
        if self.config.run_causal:
            from ..causal import CausalEnhancer

            self.causal_enhancer = CausalEnhancer(
                enable_circuit_breaker=self.config.causal_enable_circuit_breaker,
                circuit_breaker_threshold=self.config.causal_circuit_breaker_threshold,
            )

    def load_repository(self, source: str | Path | RepositoryHandle) -> Repo:
        """Load a repository from a managed workspace or streamed archive."""

        if isinstance(source, RepositoryHandle):
            repo = self._load_from_handle(source)
        else:
            repo = Repo(str(source))
        if repo.bare:
            raise ValueError("Repository is bare")
        self.repo = repo
        return repo

    def _load_from_handle(self, handle: RepositoryHandle) -> Repo:
        if handle.workspace_path:
            repo_path = Path(handle.workspace_path)
        elif handle.archive_path:
            repo_path = Path(tempfile.mkdtemp(prefix="lift_repo_"))
            shutil.unpack_archive(str(handle.archive_path), repo_path)
        else:
            raise ValueError("Repository handle missing workspace or archive path")

        if (repo_path / ".git").exists():
            repo = Repo(str(repo_path))
        else:
            repo = Repo.init(repo_path)
        if handle.branch:
            self._checkout_branch(repo, handle.branch)
        return repo

    def _checkout_branch(self, repo: Repo, branch: str) -> None:
        try:
            repo.git.checkout(branch)
        except GitCommandError:
            if "origin" in repo.remotes:
                repo.remotes.origin.fetch(branch)
                repo.git.checkout("-B", branch, f"origin/{branch}")
            else:
                raise

    def discover_python_files(self, exclude_patterns: list[str] | None = None) -> list[Path]:
        """Find all Python files in the repository.

        Args:
            exclude_patterns: Directory patterns to exclude from search.

        Returns:
            List of Python file paths relative to repository root.

        Raises:
            RepositoryNotLoadedError: If repository is not loaded.
        """
        if not self.repo:
            raise RepositoryNotLoadedError("Repository must be loaded before discovering files")

        repo_path = Path(self.repo.working_tree_dir)
        exclude = exclude_patterns or [
            "venv",
            ".venv",
            "node_modules",
            "__pycache__",
            ".git",
            "build",
            "dist",
            ".eggs",
            ".egg-info",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "htmlcov",
        ]

        python_files = []
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        skipped_large_files = []

        for py_file in repo_path.rglob("*.py"):
            # Skip if any part of the path matches excluded directories
            if any(excl in py_file.parts for excl in exclude if "*" not in excl):
                continue
            # Skip if matches exclude pattern with wildcards
            if any(py_file.match(excl) for excl in exclude if "*" in excl):
                continue

            # Check file size limit
            try:
                file_size = py_file.stat().st_size
                if file_size > max_size_bytes:
                    size_mb = file_size / (1024 * 1024)
                    skipped_large_files.append((py_file.relative_to(repo_path), size_mb))
                    self._record_progress(
                        f"skipped:{py_file.relative_to(repo_path)}:too large ({size_mb:.1f}MB)"
                    )
                    continue
            except (OSError, FileNotFoundError):
                # Skip files that can't be read
                continue

            python_files.append(py_file.relative_to(repo_path))

        if skipped_large_files:
            self._record_progress(
                f"skipped {len(skipped_large_files)} large files (>{self.config.max_file_size_mb}MB)"
            )

        return sorted(python_files)

    def lift_all(
        self,
        max_files: int | None = None,
        progress_callback: callable[[str, int, int]] | None = None,
    ) -> list[IntermediateRepresentation]:
        """Lift specifications for all Python files in the repository.

        Args:
            max_files: Optional limit on number of files to analyze. If None, uses config.max_files.
            progress_callback: Optional callback function(file_path, current, total) called for each file.

        Returns:
            List of intermediate representations, one per successfully analyzed file.

        Raises:
            RepositoryNotLoadedError: If repository is not loaded.
            TotalTimeLimitExceededError: If total time limit is exceeded.
        """
        import signal
        import time

        files = self.discover_python_files()

        # Apply file limit from parameter or config
        effective_max = max_files or self.config.max_files
        if effective_max and len(files) > effective_max:
            self._record_progress(f"limiting to first {effective_max} of {len(files)} files")
            files = files[:effective_max]

        irs: list[IntermediateRepresentation] = []
        failed: list[tuple[Path, str]] = []
        start_time = time.time()

        for i, file_path in enumerate(files, 1):
            # Check total time limit
            if self.config.max_total_time_seconds:
                elapsed = time.time() - start_time
                if elapsed > self.config.max_total_time_seconds:
                    self._record_progress(
                        f"total time limit exceeded ({elapsed:.1f}s > {self.config.max_total_time_seconds}s)"
                    )
                    raise TotalTimeLimitExceededError(
                        elapsed=elapsed,
                        limit=self.config.max_total_time_seconds,
                        files_analyzed=i - 1,
                        total_files=len(files),
                    )

            self._record_progress(f"analyzing:{file_path}:{i}/{len(files)}")

            # Call progress callback for real-time updates
            if progress_callback:
                progress_callback(str(file_path), i, len(files))

            try:
                # Set up timeout if configured
                if self.config.timeout_per_file_seconds:

                    def timeout_handler(signum, frame):
                        raise TimeoutError(
                            f"Analysis timed out after {self.config.timeout_per_file_seconds}s"
                        )

                    # Set the signal handler and alarm (Unix/Linux only)
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(self.config.timeout_per_file_seconds))

                try:
                    ir = self.lift(str(file_path))
                    irs.append(ir)
                    self._record_progress(f"success:{file_path}")
                finally:
                    # Cancel the alarm
                    if self.config.timeout_per_file_seconds:
                        signal.alarm(0)

            except TimeoutError:
                # Wrap in our custom exception for better context
                error = AnalysisTimeoutError(
                    file_path=str(file_path), timeout_seconds=self.config.timeout_per_file_seconds
                )
                error_msg = f"timeout:{file_path}:{error}"
                self._record_progress(error_msg)
                failed.append((file_path, str(error)))
            except AnalysisError as e:
                # Already wrapped, just log and continue
                error_msg = f"error:{file_path}:{e}"
                self._record_progress(error_msg)
                failed.append((file_path, str(e)))
            except Exception as e:
                # Wrap unexpected errors for better context
                wrapped_error = AnalysisError(file_path=str(file_path), original_error=e)
                error_msg = f"error:{file_path}:{wrapped_error}"
                self._record_progress(error_msg)
                failed.append((file_path, str(wrapped_error)))

        elapsed_total = time.time() - start_time
        if failed:
            self._record_progress(
                f"completed with {len(failed)} failures out of {len(files)} in {elapsed_total:.1f}s"
            )
        else:
            self._record_progress(
                f"completed successfully: {len(irs)} files analyzed in {elapsed_total:.1f}s"
            )

        return irs

    def lift(
        self, target_module: str, include_causal: bool | None = None
    ) -> IntermediateRepresentation:
        """Lift a specification from a single module.

        Args:
            target_module: Path to the Python module to analyze.
            include_causal: Override config.run_causal for this specific lift.
                If None, uses config.run_causal. If True/False, overrides config.

        Returns:
            Intermediate representation of the module. Returns EnhancedIR if
            causal analysis is enabled and successful, otherwise returns base IR.

        Raises:
            RepositoryNotLoadedError: If repository is not loaded.
            AnalysisError: If analysis fails for any reason.
        """
        if not self.repo:
            raise RepositoryNotLoadedError("Repository must be loaded before analysis")
        self.progress_log = []
        self._record_progress("reverse:start")
        repo_path = str(Path(self.repo.working_tree_dir))
        codeql_findings: list[Finding] = []
        if self.config.run_codeql and self.config.codeql_queries:
            self._record_progress("analysis:codeql:start")
            codeql_findings = self.codeql.run(repo_path, self.config.codeql_queries)
            self._record_progress("analysis:codeql:complete")

        daikon_findings: list[Finding] = []
        if self.config.run_daikon:
            self._record_progress("analysis:daikon:start")
            daikon_findings = self.daikon.run(repo_path, self.config.daikon_entrypoint)
            self._record_progress("analysis:daikon:complete")

        stack_findings: list[Finding] = []
        if self.config.run_stack_graphs and self.config.stack_index_path:
            self.stack_graphs.set_index_root(self.config.stack_index_path)
            self._record_progress("analysis:stack_graph:start")
            stack_findings = self.stack_graphs.run(target_module)
            self._record_progress("analysis:stack_graph:complete")

        evidence, evidence_lookup = self._bundle_evidence(
            codeql_findings, daikon_findings, stack_findings
        )

        intent = self._build_intent(codeql_findings, evidence_lookup)
        signature = SigClause(
            name=Path(target_module).stem,
            parameters=[Parameter(name="x", type_hint="int", description="example parameter")],
            returns="int",
            holes=[
                TypedHole(
                    identifier="return_contract",
                    type_hint="Predicate",
                    description="Assist needed: populate formal return condition",
                    constraints={
                        "provenance": "reverse",
                        "evidence_id": evidence_lookup.get("signature:return"),
                    },
                    kind=HoleKind.SIGNATURE,
                )
            ],
        )
        effects = self._build_effects(stack_findings, evidence_lookup)
        assertions = self._build_assertions(daikon_findings, evidence_lookup)

        metadata = Metadata(
            source_path=target_module,
            origin="reverse",
            language="python",
            evidence=evidence,
        )
        self._record_progress("reverse:ir-assembled")

        base_ir = IntermediateRepresentation(
            intent=intent,
            signature=signature,
            effects=effects,
            assertions=assertions,
            metadata=metadata,
        )

        # Determine if causal analysis should run (parameter overrides config)
        should_run_causal = include_causal if include_causal is not None else self.config.run_causal

        # Add causal analysis if enabled
        if should_run_causal and self.causal_enhancer:
            import ast

            from ..causal import EnhancedIR

            self._record_progress("causal:start")

            try:
                # Read source code and parse AST
                module_path = Path(self.repo.working_tree_dir) / target_module
                with open(module_path) as f:
                    source_code = f.read()
                ast_tree = ast.parse(source_code)

                # Enhance with causal capabilities
                result = self.causal_enhancer.enhance(
                    ir=base_ir,
                    ast_tree=ast_tree,
                    mode=self.config.causal_mode,
                    source_code={Path(target_module).stem: source_code},
                )

                # Create EnhancedIR
                enhanced_ir = EnhancedIR.from_enhancement_result(result)
                self._record_progress("causal:complete")
                return enhanced_ir

            except Exception as e:
                # Graceful degradation: log error and return base IR
                self._record_progress(f"causal:failed:{type(e).__name__}:{e}")
                return base_ir

        return base_ir

    def _record_progress(self, label: str) -> None:
        self.progress_log.append(label)

    def _bundle_evidence(
        self, *groups: Iterable[Finding]
    ) -> tuple[list[dict[str, object]], dict[object, str]]:
        bundles: list[dict[str, object]] = []
        lookup: dict[object, str] = {}
        counter = 0
        for group in groups:
            for finding in group:
                evidence_id = f"{finding.kind}-{counter}"
                bundles.append(
                    {
                        "id": evidence_id,
                        "analysis": finding.kind,
                        "location": finding.location,
                        "message": finding.message,
                        "metadata": finding.metadata,
                    }
                )
                lookup[id(finding)] = evidence_id
                counter += 1
        # Provide a stable evidence id for signature holes even without findings
        if all(bundle["id"] != "reverse-signature" for bundle in bundles):
            bundles.append(
                {
                    "id": "reverse-signature",
                    "analysis": "reverse",
                    "location": "signature:return",
                    "message": "Signature return contract requires confirmation",
                    "metadata": {},
                }
            )
        lookup.setdefault("signature:return", "reverse-signature")
        return bundles, lookup

    def _build_intent(
        self, findings: list[Finding], evidence_lookup: dict[object, str]
    ) -> IntentClause:
        summary = "Lifted intent with typed holes"
        holes = [
            TypedHole(
                identifier="intent_gap",
                type_hint="Description",
                description=finding.message,
                constraints={
                    "provenance": finding.kind,
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.INTENT,
            )
            for finding in findings
        ]
        return IntentClause(summary=summary, rationale="Derived from static analysis", holes=holes)

    def _build_assertions(
        self, findings: list[Finding], evidence_lookup: dict[object, str]
    ) -> list[AssertClause]:
        assertions: list[AssertClause] = []
        for index, finding in enumerate(findings):
            predicate = finding.metadata.get("predicate", "True")
            description = (
                f"Assist needed: Clarify invariant from {finding.kind}"
                if finding.metadata.get("ambiguous")
                else f"Clarify invariant from {finding.kind}"
            )
            hole = TypedHole(
                identifier=f"assertion_detail_{index}",
                type_hint="Predicate",
                description=description,
                constraints={
                    "provenance": finding.kind,
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.ASSERTION,
            )
            assertions.append(
                AssertClause(
                    predicate=predicate,
                    rationale=finding.message,
                    holes=[hole],
                )
            )
        return assertions

    def _build_effects(
        self, findings: list[Finding], evidence_lookup: dict[object, str]
    ) -> list[EffectClause]:
        if not findings:
            return [EffectClause(description="Reads external API", holes=[])]

        effects: list[EffectClause] = []
        for index, finding in enumerate(findings):
            ambiguous = bool(finding.metadata.get("ambiguous"))
            description = (
                f"Assist needed: Disambiguate {finding.message}" if ambiguous else finding.message
            )
            hole_description = (
                f"Assist needed: Resolve {finding.metadata.get('relation', 'relationship')}"
                if ambiguous
                else f"Confirm {finding.metadata.get('relation', 'relationship')} details"
            )
            hole = TypedHole(
                identifier=f"effect_detail_{index}",
                type_hint="SymbolRelationship",
                description=hole_description,
                constraints={
                    "provenance": finding.kind,
                    "relation": finding.metadata.get("relation", "relationship"),
                    "evidence_id": evidence_lookup.get(id(finding)),
                },
                kind=HoleKind.EFFECT,
            )
            effects.append(EffectClause(description=description, holes=[hole]))
        return effects


__all__ = [
    "LifterConfig",
    "SpecificationLifter",
    "RepositoryHandle",
    # Exceptions
    "LifterError",
    "RepositoryNotLoadedError",
    "AnalysisTimeoutError",
    "TotalTimeLimitExceededError",
    "AnalysisError",
    "FileTooLargeError",
]
