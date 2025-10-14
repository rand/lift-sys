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
        self._cache: dict[str, Any] = {}
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

        # Try to get types and functions from LSP if we have a valid file
        available_types = []
        available_functions = []

        if target_file is None:
            # Find a relevant Python file in the repository
            target_file = self._find_relevant_file(keywords)

        if target_file and target_file.exists():
            try:
                # Get symbols from the file using LSP
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
        """Get document symbols from LSP server."""
        if not self._lsp or not self._started:
            return []

        try:
            # Get relative path from repository root
            relative_path = str(file_path.relative_to(self.config.repository_path))

            # Open the file context (regular context manager, not async)
            with self._lsp.open_file(relative_path):
                # Request document symbols
                symbols = await self._lsp.request_document_symbols(relative_path)
                return symbols if symbols else []
        except Exception as e:
            logger.debug(f"Error getting document symbols: {e}")
            return []

    def _find_relevant_file(self, keywords: list[str]) -> Path | None:
        """Find most relevant Python file based on keywords."""
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
                        "tests",
                    ]
                )
            ]

            if not py_files:
                return None

            # Simple heuristic: prefer files with keyword in name
            for keyword in keywords:
                for py_file in py_files:
                    if keyword in py_file.stem.lower():
                        return py_file

            # Fall back to first available file
            return py_files[0] if py_files else None

        except Exception as e:
            logger.debug(f"Error finding relevant file: {e}")
            return None

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


__all__ = ["LSPSemanticContextProvider", "LSPConfig"]
