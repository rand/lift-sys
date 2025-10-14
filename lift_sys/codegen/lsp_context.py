"""LSP-based semantic context provider for code generation.

This module provides semantic context using Language Server Protocol (LSP)
servers to get real-time information from actual codebases, replacing the
knowledge base approach from PoC 2.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from multilspy import LanguageServer
from multilspy.multilspy_config import MultilspyConfig

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

            self._lsp = LanguageServer.create(
                multilspy_config,
                None,  # logger
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

        # For now, we'll use a simplified approach:
        # Get import patterns based on keywords (doesn't require LSP)
        import_patterns = self._get_imports_for_keywords(keywords)

        # Get conventions (language-specific, doesn't require LSP)
        conventions = self._get_conventions()

        # TODO: Implement actual LSP queries for types and functions
        # For now, return context with imports and conventions
        return SemanticContext(
            available_types=[],
            available_functions=[],
            import_patterns=import_patterns,
            codebase_conventions=conventions,
        )

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
