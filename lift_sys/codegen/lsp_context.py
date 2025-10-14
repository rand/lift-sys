"""LSP-based semantic context provider for code generation.

This module provides semantic context using Language Server Protocol (LSP)
servers to get real-time information from actual codebases, replacing the
knowledge base approach from PoC 2.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from multilspy import LanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger

from .lsp_cache import LSPCache
from .lsp_metrics import LSPMetricsCollector
from .semantic_context import (
    ImportPattern,
    SemanticContext,
    SemanticContextProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class LSPConfig:
    """Configuration for LSP integration."""

    repository_path: Path
    """Path to the repository to analyze."""

    language: str = "python"
    """Programming language (python, typescript, rust, go)."""

    language_server: str | None = None
    """Language server to use (defaults based on language)."""

    cache_enabled: bool = True
    """Whether to cache LSP responses."""

    cache_ttl: int = 300
    """Cache time-to-live in seconds."""

    timeout: float = 0.5
    """Timeout for LSP requests in seconds."""

    fallback_to_knowledge_base: bool = True
    """Whether to fall back to knowledge base on errors."""

    cache_enabled: bool = True
    """Whether to enable LSP response caching."""

    metrics_enabled: bool = True
    """Whether to collect LSP metrics."""

    metrics_log_interval: float = 60.0
    """Interval in seconds to log metrics (default 60s)."""


class LSPSemanticContextProvider:
    """Provides semantic context using LSP servers.

    This replaces the knowledge base approach from PoC 2 with real-time
    semantic information from LSP servers like pyright, rust-analyzer, etc.
    """

    def __init__(self, config: LSPConfig):
        """Initialize with LSP configuration.

        Args:
            config: LSP configuration including repository path and language.
        """
        self.config = config
        self._lsp: LanguageServer | None = None
        self._lsp_context = None
        self._lsp_cache = (
            LSPCache(ttl=config.cache_ttl, max_size=1000) if config.cache_enabled else None
        )
        self._metrics = LSPMetricsCollector() if config.metrics_enabled else None
        self._knowledge_base_fallback = SemanticContextProvider(language=config.language)
        self._started = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the LSP server."""
        if self._started:
            return

        try:
            logger.info(
                f"Starting LSP server for {self.config.language} at {self.config.repository_path}"
            )

            multilspy_config = MultilspyConfig.from_dict(
                {
                    "code_language": self.config.language,
                    "trace_lsp_communication": False,
                }
            )

            # Create multilspy logger
            multilspy_logger = MultilspyLogger()

            self._lsp = LanguageServer.create(
                multilspy_config,
                multilspy_logger,
                str(self.config.repository_path),
            )

            # start_server() returns a context manager, enter it
            self._lsp_context = self._lsp.start_server()
            await self._lsp_context.__aenter__()
            self._started = True
            logger.info("LSP server started successfully")

        except Exception as e:
            logger.warning(f"Failed to start LSP server: {e}")
            if not self.config.fallback_to_knowledge_base:
                raise
            logger.info("Will use knowledge base fallback")

    async def stop(self) -> None:
        """Stop the LSP server."""
        if not self._started or not self._lsp:
            return

        try:
            logger.info("Stopping LSP server")
            # Exit the context manager
            if hasattr(self, "_lsp_context") and self._lsp_context:
                await self._lsp_context.__aexit__(None, None, None)
            logger.info("LSP server stopped successfully")
        except Exception as e:
            logger.warning(f"Error stopping LSP server: {e}")
        finally:
            # Always mark as stopped, even if cleanup had errors
            self._started = False

    async def get_context_for_intent(
        self,
        intent_summary: str,
        target_file: Path | None = None,
    ) -> SemanticContext:
        """Get semantic context based on intent and target location.

        Args:
            intent_summary: Summary of what the function should do.
            target_file: Optional target file for context-aware suggestions.

        Returns:
            SemanticContext with types, functions, and import patterns.
        """
        # If LSP not started or failed, use fallback
        if not self._started or not self._lsp:
            logger.debug("LSP not available, using knowledge base fallback")
            return self._knowledge_base_fallback.get_context_for_intent(intent_summary)

        try:
            return await self._get_lsp_context(intent_summary, target_file)
        except Exception as e:
            logger.warning(f"LSP context retrieval failed: {e}")
            if self.config.fallback_to_knowledge_base:
                logger.debug("Falling back to knowledge base")
                return self._knowledge_base_fallback.get_context_for_intent(intent_summary)
            raise

    async def _get_lsp_context(
        self,
        intent_summary: str,
        target_file: Path | None,
    ) -> SemanticContext:
        """Get context from LSP server."""
        # Extract keywords from intent for querying
        keywords = self._extract_keywords(intent_summary)

        # Get import patterns based on keywords
        import_patterns = self._get_imports_for_keywords(keywords)

        # Get conventions (language-specific)
        conventions = self._get_conventions()

        # Try to get types and functions from LSP using parallel queries
        available_types = []
        available_functions = []

        # Find multiple relevant files for richer context
        if target_file is None:
            relevant_files = self._find_relevant_files(keywords, intent_summary, limit=3)
        else:
            relevant_files = [target_file] if target_file.exists() else []

        if relevant_files:
            # Query all files in parallel
            symbol_results = await self._get_symbols_from_files(relevant_files)

            # Merge and extract symbols from all files
            for file_path, symbols in symbol_results:
                if symbols:
                    types, functions = self._extract_symbols_from_response(symbols, file_path)
                    available_types.extend(types)
                    available_functions.extend(functions)

        # Rank symbols by relevance before limiting to top N
        ranked_types = self._rank_symbols(available_types, keywords, intent_summary)
        ranked_functions = self._rank_symbols(available_functions, keywords, intent_summary)

        return SemanticContext(
            available_types=ranked_types[:5],  # Top 5 most relevant types
            available_functions=ranked_functions[:5],  # Top 5 most relevant functions
            import_patterns=import_patterns,
            codebase_conventions=conventions,
        )

    async def _get_document_symbols(self, file_path: Path) -> list[dict]:
        """Get document symbols from LSP server with caching.

        Args:
            file_path: Absolute path to the file

        Returns:
            List of document symbols (may be empty)
        """
        import time

        start_time = time.time()
        cached = False
        success = True
        error_type = None
        symbols_count = 0

        if not self._lsp or not self._started:
            return []

        try:
            # Check cache first
            if self._lsp_cache:
                cached_symbols = await self._lsp_cache.get(file_path, "document_symbols")
                if cached_symbols is not None:
                    logger.debug(f"Cache hit for {file_path.name}")
                    cached = True
                    symbols_count = len(cached_symbols) if cached_symbols else 0

                    # Record metrics
                    if self._metrics:
                        latency = time.time() - start_time
                        self._metrics.record_query(
                            success=True,
                            cached=True,
                            latency=latency,
                            symbols_count=symbols_count,
                        )

                    return cached_symbols

            # Get relative path from repository root
            relative_path = str(file_path.relative_to(self.config.repository_path))

            # Open the file context (regular context manager, not async)
            with self._lsp.open_file(relative_path):
                # Request document symbols
                symbols = await self._lsp.request_document_symbols(relative_path)
                result = symbols if symbols else []
                symbols_count = len(result) if result else 0

                # Store in cache
                if self._lsp_cache and result:
                    await self._lsp_cache.put(file_path, "document_symbols", result)

                return result

        except Exception as e:
            logger.debug(f"Error getting document symbols: {e}")
            success = False
            error_type = type(e).__name__
            return []

        finally:
            # Record metrics (only if not already recorded for cache hit)
            if self._metrics and not cached:
                latency = time.time() - start_time
                self._metrics.record_query(
                    success=success,
                    cached=False,
                    latency=latency,
                    symbols_count=symbols_count,
                    error_type=error_type,
                )

                # Log metrics periodically
                if self._metrics.should_log_metrics(self.config.metrics_log_interval):
                    metrics = self._metrics.get_metrics()
                    logger.info(
                        f"LSP Metrics: {metrics.queries_total} queries, "
                        f"{metrics.query_success_rate:.1f}% success, "
                        f"{metrics.cache_hit_rate:.1f}% cache hit, "
                        f"{metrics.avg_latency_ms:.1f}ms avg latency"
                    )
                    self._metrics.mark_logged()

    async def _get_symbols_from_files(
        self, file_paths: list[Path]
    ) -> list[tuple[Path, list[dict]]]:
        """Get symbols from multiple files in parallel.

        Args:
            file_paths: List of file paths to query

        Returns:
            List of (file_path, symbols) tuples
        """
        if not file_paths:
            return []

        # Create tasks for parallel queries with timeout
        async def query_with_timeout(file_path: Path) -> tuple[Path, list[dict]]:
            try:
                symbols = await asyncio.wait_for(
                    self._get_document_symbols(file_path),
                    timeout=self.config.timeout,
                )
                return (file_path, symbols)
            except TimeoutError:
                logger.debug(f"Timeout querying {file_path.name}")
                return (file_path, [])
            except Exception as e:
                logger.debug(f"Error querying {file_path.name}: {e}")
                return (file_path, [])

        # Execute queries in parallel
        tasks = [query_with_timeout(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Query failed: {result}")
            else:
                valid_results.append(result)

        return valid_results

    def _extract_symbols_from_response(
        self, symbols: list[dict], file_path: Path
    ) -> tuple[list, list]:
        """Extract types and functions from LSP symbol response.

        Args:
            symbols: LSP document symbols response
            file_path: Path to the file these symbols came from

        Returns:
            Tuple of (types, functions) lists
        """
        from .semantic_context import FunctionInfo, TypeInfo

        types = []
        functions = []

        # Flatten the symbol list (multilspy returns list of lists)
        flat_symbols = []
        for item in symbols:
            if isinstance(item, list):
                flat_symbols.extend(item)
            elif item is not None:
                flat_symbols.append(item)

        for symbol in flat_symbols:
            if not isinstance(symbol, dict):
                continue

            symbol_kind = symbol.get("kind")
            symbol_name = symbol.get("name", "")

            # Class/Interface = types (kind 5 = Class, 11 = Interface)
            if symbol_kind in [5, 11]:
                types.append(
                    TypeInfo(
                        name=symbol_name,
                        module=str(file_path.relative_to(self.config.repository_path)),
                        description=f"Type from {file_path.name}",
                        example_usage=None,
                    )
                )

            # Function/Method (kind 6 = Method, 12 = Function)
            elif symbol_kind in [6, 12]:
                # Try to get signature from detail field
                detail = symbol.get("detail", "")
                signature = f"{symbol_name}(...)"
                if detail:
                    signature = detail

                functions.append(
                    FunctionInfo(
                        name=symbol_name,
                        module=str(file_path.relative_to(self.config.repository_path)),
                        signature=signature,
                        description=f"Function from {file_path.name}",
                    )
                )

        return types, functions

    def _rank_symbols(
        self,
        symbols: list,
        keywords: list[str],
        intent_summary: str,
    ) -> list:
        """Rank symbols by relevance to intent using compute_relevance.

        Args:
            symbols: List of TypeInfo or FunctionInfo objects
            keywords: Extracted keywords from intent
            intent_summary: Full intent description

        Returns:
            Symbols sorted by relevance score (highest first)
        """
        from .semantic_context import TypeInfo, compute_relevance

        if not symbols:
            return []

        # Score each symbol
        scored_symbols = []
        for symbol in symbols:
            symbol_type = "type" if isinstance(symbol, TypeInfo) else "function"
            score = compute_relevance(
                symbol.name,
                symbol_type,
                keywords,
                intent_summary,
            )
            scored_symbols.append((score.total, symbol))

        # Sort by score descending
        scored_symbols.sort(key=lambda x: x[0], reverse=True)

        return [symbol for _, symbol in scored_symbols]

    def _score_file_relevance(
        self, file_path: Path, keywords: list[str], intent_summary: str
    ) -> float:
        """Score file relevance to intent.

        Args:
            file_path: Path to file
            keywords: Extracted keywords from intent
            intent_summary: Full intent description

        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.0
        file_name = file_path.stem.lower()
        file_parts = [p.lower() for p in file_path.parts]
        intent_lower = intent_summary.lower()

        # Exact keyword match in filename: +0.5
        for keyword in keywords:
            if keyword == file_name:
                score += 0.5
                break
            elif keyword in file_name:
                score += 0.3
                break

        # Partial keyword match in path: +0.2
        for keyword in keywords:
            if any(keyword in part for part in file_parts):
                score += 0.2
                break

        # Intent domain heuristics
        domain_matches = {
            "api": ["api", "server", "routes", "endpoints"],
            "test": ["test", "tests", "testing"],
            "model": ["model", "models", "schema"],
            "service": ["service", "services"],
            "util": ["util", "utils", "helper", "helpers"],
        }

        for domain, indicators in domain_matches.items():
            if domain in intent_lower:
                if any(ind in file_parts for ind in indicators):
                    score += 0.2
                    break

        # Prefer certain directories
        preferred_dirs = ["core", "lib", "src", "main"]
        if any(pref in file_parts for pref in preferred_dirs):
            score += 0.1

        # Penalize test/example files unless intent mentions testing
        if "test" not in intent_lower:
            if any(test_dir in file_parts for test_dir in ["test", "tests", "testing"]):
                score *= 0.3

        # Penalize __init__.py unless explicitly looking for package structure
        if file_path.name == "__init__.py":
            score *= 0.5

        return min(score, 1.0)

    def _find_relevant_files(
        self, keywords: list[str], intent_summary: str, limit: int = 3
    ) -> list[Path]:
        """Find multiple relevant files based on keywords and intent.

        Args:
            keywords: Extracted keywords from intent
            intent_summary: Full intent description
            limit: Maximum number of files to return

        Returns:
            List of relevant file paths, sorted by relevance
        """
        try:
            # Get file extension patterns based on language
            if self.config.language == "python":
                patterns = ["*.py"]
            elif self.config.language == "typescript":
                patterns = ["*.ts", "*.tsx"]
            elif self.config.language == "rust":
                patterns = ["*.rs"]
            elif self.config.language == "go":
                patterns = ["*.go"]
            else:
                patterns = ["*.py"]  # Default to Python

            # Find all matching files
            all_files = []
            for pattern in patterns:
                all_files.extend(self.config.repository_path.rglob(pattern))

            # Filter out common non-relevant directories
            filtered_files = [
                f
                for f in all_files
                if not any(
                    excluded in f.parts
                    for excluded in [
                        "__pycache__",
                        ".venv",
                        "venv",
                        "node_modules",
                        ".git",
                        "dist",
                        "build",
                        "target",
                    ]
                )
            ]

            if not filtered_files:
                return []

            # Score all files
            scored_files = [
                (self._score_file_relevance(f, keywords, intent_summary), f) for f in filtered_files
            ]

            # Sort by score (descending) and take top N
            scored_files.sort(key=lambda x: x[0], reverse=True)

            # Filter out files with score 0 and return top results
            relevant_files = [f for score, f in scored_files[: limit * 2] if score > 0.0]

            return relevant_files[:limit]

        except Exception as e:
            logger.debug(f"Error finding relevant files: {e}")
            return []

    def _extract_keywords(self, intent_summary: str) -> list[str]:
        """Extract keywords from intent for querying."""
        # Simple keyword extraction
        words = intent_summary.lower().split()
        keywords = [
            w for w in words if len(w) > 3 and w not in ["the", "and", "for", "with", "that"]
        ]
        return keywords

    def _get_imports_for_keywords(self, keywords: list[str]) -> list[ImportPattern]:
        """Get import patterns based on keywords."""
        patterns = []

        if self.config.language == "python":
            # File/path operations
            if any(kw in keywords for kw in ["file", "path", "directory", "folder"]):
                patterns.append(
                    ImportPattern(
                        module="pathlib",
                        common_imports=["Path"],
                        usage_context="File system operations",
                    )
                )

            # Time/date operations
            if any(kw in keywords for kw in ["time", "date", "timestamp", "datetime"]):
                patterns.append(
                    ImportPattern(
                        module="datetime",
                        common_imports=["datetime", "timedelta"],
                        usage_context="Date and time operations",
                    )
                )

            # Pattern matching
            if any(kw in keywords for kw in ["pattern", "regex", "match", "validate", "email"]):
                patterns.append(
                    ImportPattern(
                        module="re",
                        common_imports=["match", "search", "compile"],
                        usage_context="Pattern matching and validation",
                    )
                )

            # Decimal operations
            if any(kw in keywords for kw in ["decimal", "money", "price", "currency"]):
                patterns.append(
                    ImportPattern(
                        module="decimal",
                        common_imports=["Decimal"],
                        usage_context="Precise decimal arithmetic",
                    )
                )

            # Always include typing for Python
            patterns.append(
                ImportPattern(
                    module="typing",
                    common_imports=["Any", "Optional", "Union", "List", "Dict"],
                    usage_context="Type annotations",
                )
            )

        elif self.config.language == "typescript":
            # File/path operations
            if any(kw in keywords for kw in ["file", "path", "directory", "folder"]):
                patterns.append(
                    ImportPattern(
                        module="fs",
                        common_imports=["promises as fs"],
                        usage_context="File system operations",
                    )
                )
                patterns.append(
                    ImportPattern(
                        module="path",
                        common_imports=["join", "resolve", "dirname"],
                        usage_context="Path manipulation",
                    )
                )

            # Time/date operations
            if any(kw in keywords for kw in ["time", "date", "timestamp", "datetime"]):
                patterns.append(
                    ImportPattern(
                        module="date-fns",
                        common_imports=["format", "parseISO", "addDays"],
                        usage_context="Date and time operations",
                    )
                )

            # HTTP/API operations
            if any(kw in keywords for kw in ["http", "api", "fetch", "request", "endpoint"]):
                patterns.append(
                    ImportPattern(
                        module="axios",
                        common_imports=["axios"],
                        usage_context="HTTP requests",
                    )
                )

            # Async operations
            if any(kw in keywords for kw in ["async", "promise", "await"]):
                patterns.append(
                    ImportPattern(
                        module="",  # Built-in
                        common_imports=["Promise"],
                        usage_context="Asynchronous operations",
                    )
                )

        return patterns

    def _get_conventions(self) -> dict[str, str]:
        """Get coding conventions for the language."""
        if self.config.language == "python":
            return {
                "error_handling": "Use try/except blocks for operations that may fail",
                "type_hints": "Always include type hints for function parameters and returns",
                "docstrings": "Use Google-style docstrings with Args and Returns sections",
                "imports": "Group imports: standard library, third-party, local",
            }
        elif self.config.language == "typescript":
            return {
                "error_handling": "Use try/catch blocks, prefer explicit error types",
                "type_annotations": "Always include type annotations for function parameters and returns",
                "docstrings": "Use TSDoc format with @param, @returns, and @example tags",
                "imports": "Use ES6 import/export syntax, group imports logically",
                "async": "Use async/await for asynchronous operations, return Promise types",
                "null_safety": "Use optional chaining (?.) and nullish coalescing (??)",
            }
        return {}

    def get_metrics(self) -> dict[str, Any]:
        """Get LSP performance metrics.

        Returns:
            Metrics dictionary with query counts, latency, cache stats, etc.
        """
        if self._metrics:
            metrics = self._metrics.get_metrics()
            result = metrics.to_dict()
            # Add cache stats if available
            if self._lsp_cache:
                result["cache"] = self._lsp_cache.stats()
            return result
        return {"enabled": False}

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dict, or empty dict if caching disabled
        """
        if self._lsp_cache:
            return self._lsp_cache.stats()
        return {"enabled": False}


__all__ = ["LSPSemanticContextProvider", "LSPConfig"]
