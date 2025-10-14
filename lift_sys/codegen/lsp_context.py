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
            self._started = False
            logger.info("LSP server stopped successfully")
        except Exception as e:
            logger.warning(f"Error stopping LSP server: {e}")

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

        # Try to get types and functions from LSP
        available_types = []
        available_functions = []

        # Find relevant files (multiple for richer context)
        if target_file is None:
            relevant_files = self._find_relevant_files(keywords, intent_summary, limit=1)
            target_file = relevant_files[0] if relevant_files else None

        if target_file and target_file.exists():
            try:
                # Get symbols from the file using LSP (with caching)
                symbols = await asyncio.wait_for(
                    self._get_document_symbols(target_file),
                    timeout=self.config.timeout,
                )

                # Extract types and functions from symbols
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
                        from .semantic_context import TypeInfo

                        available_types.append(
                            TypeInfo(
                                name=symbol_name,
                                module=str(target_file.relative_to(self.config.repository_path)),
                                description=f"Type from {target_file.name}",
                                example_usage=None,
                            )
                        )

                    # Function/Method (kind 6 = Method, 12 = Function)
                    elif symbol_kind in [6, 12]:
                        from .semantic_context import FunctionInfo

                        # Try to get signature from detail field
                        detail = symbol.get("detail", "")
                        signature = f"{symbol_name}(...)"
                        if detail:
                            signature = detail

                        available_functions.append(
                            FunctionInfo(
                                name=symbol_name,
                                module=str(target_file.relative_to(self.config.repository_path)),
                                signature=signature,
                                description=f"Function from {target_file.name}",
                            )
                        )

            except Exception as e:
                logger.debug(f"Failed to get LSP symbols: {e}")
                # Continue with just import patterns and conventions

        return SemanticContext(
            available_types=available_types[:5],  # Limit to top 5
            available_functions=available_functions[:5],  # Limit to top 5
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
        if not self._lsp or not self._started:
            return []

        # Check cache first
        if self._lsp_cache:
            cached_symbols = await self._lsp_cache.get(file_path, "document_symbols")
            if cached_symbols is not None:
                logger.debug(f"Cache hit for {file_path.name}")
                return cached_symbols

        try:
            # Get relative path from repository root
            relative_path = str(file_path.relative_to(self.config.repository_path))

            # Open the file context (regular context manager, not async)
            with self._lsp.open_file(relative_path):
                # Request document symbols
                symbols = await self._lsp.request_document_symbols(relative_path)
                result = symbols if symbols else []

                # Store in cache
                if self._lsp_cache and result:
                    await self._lsp_cache.put(file_path, "document_symbols", result)

                return result
        except Exception as e:
            logger.debug(f"Error getting document symbols: {e}")
            return []

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
            # Get all Python files in repository
            py_files = list(self.config.repository_path.rglob("*.py"))

            # Filter out common non-relevant directories
            py_files = [
                f
                for f in py_files
                if not any(
                    excluded in f.parts
                    for excluded in [
                        "__pycache__",
                        ".venv",
                        "venv",
                        "node_modules",
                        ".git",
                    ]
                )
            ]

            if not py_files:
                return []

            # Score all files
            scored_files = [
                (self._score_file_relevance(f, keywords, intent_summary), f) for f in py_files
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
        if self.config.language != "python":
            return []

        patterns = []

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

        # Always include typing
        patterns.append(
            ImportPattern(
                module="typing",
                common_imports=["Any", "Optional", "Union", "List", "Dict"],
                usage_context="Type annotations",
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
        return {}

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dict, or empty dict if caching disabled
        """
        if self._lsp_cache:
            return self._lsp_cache.stats()
        return {"enabled": False}


__all__ = ["LSPSemanticContextProvider", "LSPConfig"]
