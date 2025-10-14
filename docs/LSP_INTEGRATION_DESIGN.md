# LSP Integration Design for Semantic Context

**Version**: 1.0
**Date**: October 14, 2025
**Status**: Week 5-6 Implementation Plan
**Related**: INTEGRATION_ROADMAP.md Week 5-6

---

## Executive Summary

This document outlines the design for integrating Language Server Protocol (LSP) support into lift-sys's semantic context system. Building on the PoC 2 validation (1.17x average, 1.58x peak quality improvement with semantic context), this integration replaces the knowledge base approach with real-time semantic information from LSP servers.

**Key Goals:**
- Real-time semantic context from actual codebases (not static knowledge base)
- Dynamic type information, function signatures, and import patterns
- Language-agnostic approach supporting Python, TypeScript, Rust, Go
- Measurable quality improvement (target: 1.4-1.6x in real-world usage)

**Key Technology:**
- **multilspy**: Microsoft's Python LSP client library
- **pyright**: Primary language server for Python type checking
- **LSP Protocol**: Standard protocol for semantic code analysis

---

## Architecture Overview

```
SemanticCodeGenerator
    ↓
LSPSemanticContextProvider
    ↓
multilspy (LSP Client)
    ↓
pyright / rust-analyzer / typescript-language-server / gopls
    ↓
Repository Code
```

### Key Components

1. **LSPSemanticContextProvider**: New class extending/replacing SemanticContextProvider
2. **LSPClient**: Wrapper around multilspy for lifecycle management
3. **SemanticContextCache**: Cache layer for LSP responses
4. **FallbackStrategy**: Graceful degradation to knowledge base on errors

---

## Detailed Design

### 1. LSPSemanticContextProvider

```python
# File: lift_sys/codegen/lsp_context.py

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from multilspy import LanguageServer
from multilspy.multilspy_config import MultilspyConfig

from .semantic_context import (
    SemanticContext,
    TypeInfo,
    FunctionInfo,
    ImportPattern,
)


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
        self._cache: dict[str, Any] = {}
        self._knowledge_base_fallback = self._build_fallback()

    async def start(self) -> None:
        """Start the LSP server."""
        multilspy_config = MultilspyConfig.from_dict({
            "code_language": self.config.language,
            "trace_lsp_communication": False,
        })

        self._lsp = LanguageServer.create(
            multilspy_config,
            None,  # logger
            str(self.config.repository_path),
        )

        await self._lsp.start_server()

    async def stop(self) -> None:
        """Stop the LSP server."""
        if self._lsp:
            await self._lsp.stop()

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
        try:
            # Try to get context from LSP
            return await self._get_lsp_context(intent_summary, target_file)
        except Exception as e:
            if self.config.fallback_to_knowledge_base:
                # Fall back to knowledge base on error
                return self._knowledge_base_fallback.get_context_for_intent(intent_summary)
            raise

    async def _get_lsp_context(
        self,
        intent_summary: str,
        target_file: Path | None,
    ) -> SemanticContext:
        """Get context from LSP server."""
        if not self._lsp:
            raise RuntimeError("LSP server not started. Call start() first.")

        # Extract keywords from intent for querying
        keywords = self._extract_keywords(intent_summary)

        # Query LSP for relevant information
        available_types = await self._get_types(keywords, target_file)
        available_functions = await self._get_functions(keywords, target_file)
        import_patterns = await self._get_imports(keywords, target_file)
        conventions = await self._get_conventions(target_file)

        return SemanticContext(
            available_types=available_types,
            available_functions=available_functions,
            import_patterns=import_patterns,
            codebase_conventions=conventions,
        )

    async def _get_types(
        self,
        keywords: list[str],
        target_file: Path | None,
    ) -> list[TypeInfo]:
        """Get available types using LSP completions and hover."""
        if target_file is None:
            # Find relevant files in repository
            target_file = self._find_relevant_file(keywords)

        types: list[TypeInfo] = []

        # Use LSP completion to find type suggestions
        async with self._lsp.open_file(str(target_file)):
            # Request completions at the end of the file
            completions = await asyncio.wait_for(
                self._lsp.request_completions(
                    str(target_file),
                    line=0,  # TODO: Better position selection
                    column=0,
                ),
                timeout=self.config.timeout,
            )

            # Filter to types (classes, interfaces, etc.)
            for completion in completions:
                if completion.kind in [7, 8, 22]:  # Class, Interface, Struct
                    # Get hover info for detailed description
                    hover = await self._get_hover_info(
                        target_file,
                        completion.label,
                    )

                    types.append(TypeInfo(
                        name=completion.label,
                        module=self._extract_module(hover),
                        description=self._extract_description(hover),
                        example_usage=self._generate_example(completion),
                    ))

        return types[:5]  # Limit to top 5

    async def _get_functions(
        self,
        keywords: list[str],
        target_file: Path | None,
    ) -> list[FunctionInfo]:
        """Get available functions using LSP document symbols."""
        if target_file is None:
            target_file = self._find_relevant_file(keywords)

        functions: list[FunctionInfo] = []

        # Get all symbols in the file
        symbols = await asyncio.wait_for(
            self._lsp.request_document_symbols(str(target_file)),
            timeout=self.config.timeout,
        )

        # Filter to functions/methods
        for symbol in symbols:
            if symbol.kind in [6, 12]:  # Method, Function
                # Get hover info for signature
                hover = await self._get_hover_info(
                    target_file,
                    symbol.name,
                )

                functions.append(FunctionInfo(
                    name=symbol.name,
                    module=str(target_file),
                    signature=self._extract_signature(hover),
                    description=self._extract_description(hover),
                ))

        return functions[:5]  # Limit to top 5

    async def _get_imports(
        self,
        keywords: list[str],
        target_file: Path | None,
    ) -> list[ImportPattern]:
        """Get common import patterns from repository."""
        # Analyze import statements across repository
        # This could use references to find commonly imported modules

        # For now, return most common patterns for the language
        if self.config.language == "python":
            return self._get_python_common_imports(keywords)

        return []

    async def _get_conventions(
        self,
        target_file: Path | None,
    ) -> dict[str, str]:
        """Extract coding conventions from repository."""
        # Could analyze existing code to infer conventions
        # For now, return language defaults

        if self.config.language == "python":
            return {
                "error_handling": "Use try/except blocks for operations that may fail",
                "type_hints": "Always include type hints for function parameters and returns",
                "docstrings": "Use Google-style docstrings with Args and Returns sections",
                "imports": "Group imports: standard library, third-party, local",
            }

        return {}

    async def _get_hover_info(
        self,
        file_path: Path,
        symbol_name: str,
    ) -> str:
        """Get hover information for a symbol."""
        # This is a simplified version
        # In practice, we'd need to find the exact position of the symbol
        hover = await self._lsp.request_hover(
            str(file_path),
            line=0,  # TODO: Find symbol position
            column=0,
        )
        return hover.contents if hover else ""

    def _extract_keywords(self, intent_summary: str) -> list[str]:
        """Extract keywords from intent for querying."""
        # Simple keyword extraction
        # TODO: More sophisticated NLP-based extraction
        words = intent_summary.lower().split()
        keywords = [
            w for w in words
            if len(w) > 3 and w not in ["the", "and", "for", "with", "that"]
        ]
        return keywords

    def _find_relevant_file(self, keywords: list[str]) -> Path:
        """Find most relevant file based on keywords."""
        # TODO: Better file selection logic
        # For now, return a common file or __init__.py
        repo_files = list(self.config.repository_path.rglob("*.py"))
        if repo_files:
            return repo_files[0]
        return self.config.repository_path / "main.py"

    def _extract_module(self, hover_text: str) -> str:
        """Extract module name from hover text."""
        # Parse hover markdown to extract module
        # TODO: Implement proper parsing
        return "unknown"

    def _extract_description(self, hover_text: str) -> str:
        """Extract description from hover text."""
        # Parse hover markdown to extract description
        # TODO: Implement proper parsing
        return hover_text[:100] if hover_text else "No description"

    def _extract_signature(self, hover_text: str) -> str:
        """Extract function signature from hover text."""
        # Parse hover markdown to extract signature
        # TODO: Implement proper parsing
        lines = hover_text.split("\n")
        for line in lines:
            if "def " in line or "(" in line:
                return line.strip()
        return "unknown_signature()"

    def _generate_example(self, completion) -> str:
        """Generate example usage from completion."""
        # TODO: Better example generation
        return f"{completion.label}(...)"

    def _get_python_common_imports(self, keywords: list[str]) -> list[ImportPattern]:
        """Get common Python imports based on keywords."""
        patterns = []

        if any(kw in keywords for kw in ["file", "path", "directory"]):
            patterns.append(ImportPattern(
                module="pathlib",
                common_imports=["Path"],
                usage_context="File system operations",
            ))

        if any(kw in keywords for kw in ["time", "date", "timestamp"]):
            patterns.append(ImportPattern(
                module="datetime",
                common_imports=["datetime", "timedelta"],
                usage_context="Date and time operations",
            ))

        if any(kw in keywords for kw in ["pattern", "regex", "match", "validate"]):
            patterns.append(ImportPattern(
                module="re",
                common_imports=["match", "search", "compile"],
                usage_context="Pattern matching and validation",
            ))

        # Always include typing
        patterns.append(ImportPattern(
            module="typing",
            common_imports=["Any", "Optional", "Union", "List", "Dict"],
            usage_context="Type annotations",
        ))

        return patterns

    def _build_fallback(self):
        """Build knowledge base fallback."""
        from .semantic_context import SemanticContextProvider
        return SemanticContextProvider(language=self.config.language)


__all__ = ["LSPSemanticContextProvider", "LSPConfig"]
```

---

## Integration Strategy

### Phase 1: Basic LSP Integration (Days 1-2)

**Tasks:**
1. Install dependencies:
   ```bash
   uv add multilspy pyright
   ```

2. Create `lift_sys/codegen/lsp_context.py` with LSPSemanticContextProvider

3. Write unit tests:
   ```python
   # tests/integration/test_lsp_context.py
   @pytest.mark.asyncio
   async def test_lsp_context_provider_python():
       config = LSPConfig(
           repository_path=Path("/path/to/test/repo"),
           language="python",
       )
       provider = LSPSemanticContextProvider(config)

       async with provider:
           context = await provider.get_context_for_intent(
               "validate email addresses"
           )

           assert len(context.available_types) > 0
           assert len(context.import_patterns) > 0
   ```

**Success Criteria:**
- LSP server starts and stops cleanly
- Can retrieve types and functions from test repository
- Graceful fallback to knowledge base on errors

---

### Phase 2: SemanticCodeGenerator Integration (Days 3-4)

**Tasks:**
1. Update SemanticCodeGenerator to use LSPSemanticContextProvider:
   ```python
   # lift_sys/codegen/semantic_generator.py

   class SemanticCodeGenerator(XGrammarCodeGenerator):
       def __init__(
           self,
           provider: BaseProvider,
           config: CodeGeneratorConfig | None = None,
           language: str = "python",
           repository_path: Path | None = None,
       ):
           super().__init__(provider, config)
           self.language = language

           if repository_path:
               # Use LSP-based context
               lsp_config = LSPConfig(
                   repository_path=repository_path,
                   language=language,
               )
               self.context_provider = LSPSemanticContextProvider(lsp_config)
           else:
               # Fall back to knowledge base
               self.context_provider = SemanticContextProvider(language=language)
   ```

2. Add lifecycle management:
   ```python
   async def __aenter__(self):
       if isinstance(self.context_provider, LSPSemanticContextProvider):
           await self.context_provider.start()
       return self

   async def __aexit__(self, exc_type, exc_val, exc_tb):
       if isinstance(self.context_provider, LSPSemanticContextProvider):
           await self.context_provider.stop()
   ```

3. Update tests to use async context manager

**Success Criteria:**
- SemanticCodeGenerator works with both LSP and knowledge base contexts
- LSP lifecycle managed properly (no leaked processes)
- All existing tests still pass

---

### Phase 3: Quality Validation (Days 5-6)

**Tasks:**
1. Create validation script:
   ```bash
   experiments/validate_lsp_quality.py
   ```

2. Compare knowledge base vs LSP context:
   - Baseline: Knowledge base (PoC 2: 1.17x)
   - Enhanced: LSP-based context
   - Target: 1.4-1.6x improvement

3. Test on real repositories:
   - lift-sys itself
   - Popular open-source Python projects
   - Measure quality improvement

4. Document results in INTEGRATION_ROADMAP.md

**Success Criteria:**
- Quality improvement >= 1.4x (better than PoC 2)
- LSP latency < 500ms per request
- Zero import errors in generated code

---

## Error Handling Strategy

### Timeout Handling
```python
try:
    result = await asyncio.wait_for(
        lsp_request(...),
        timeout=config.timeout,
    )
except asyncio.TimeoutError:
    if config.fallback_to_knowledge_base:
        return fallback_result()
    raise
```

### LSP Server Crashes
```python
try:
    context = await provider.get_context_for_intent(...)
except LSPError:
    # Restart LSP server
    await provider.stop()
    await provider.start()
    # Retry once
    context = await provider.get_context_for_intent(...)
```

### Missing Repository
```python
if not repository_path.exists():
    warnings.warn("Repository not found, using knowledge base")
    return SemanticContextProvider(language)
```

---

## Performance Considerations

### Caching Strategy
- **Cache completion results** for 5 minutes
- **Cache hover information** for 10 minutes
- **Cache document symbols** for 1 minute (more dynamic)
- **Invalidate cache** on file changes

### Connection Pooling
- Keep LSP server alive across multiple generations
- Reuse connections for same repository
- Clean up after 10 minutes of inactivity

### Parallelization
- Run LSP queries in parallel:
  ```python
  types, functions, imports = await asyncio.gather(
      self._get_types(keywords, target_file),
      self._get_functions(keywords, target_file),
      self._get_imports(keywords, target_file),
  )
  ```

---

## Testing Strategy

### Unit Tests
1. Test LSP server lifecycle
2. Test context retrieval for each method
3. Test fallback strategy
4. Test caching behavior
5. Test error handling

### Integration Tests
1. Test with real pyright on test repository
2. Test with multiple languages (Python, TypeScript)
3. Test end-to-end code generation with LSP context
4. Compare quality with/without LSP

### Performance Tests
1. Measure LSP request latency
2. Measure cache hit rate
3. Measure overall generation time
4. Profile memory usage

---

## Future Enhancements

### Multi-Language Support (Week 7-8)
- Add rust-analyzer for Rust
- Add typescript-language-server for TypeScript
- Add gopls for Go
- Test LSP context quality for each language

### Advanced Features
- **Error Correction Loop**: Use LSP diagnostics to fix generated code
- **Smart File Selection**: ML-based file relevance scoring
- **Cross-Repository Context**: Analyze dependencies for import patterns
- **Incremental Updates**: Watch file changes and update context

---

## Success Metrics

### Quantitative
- **Quality Improvement**: 1.4-1.6x over baseline (target)
- **LSP Latency**: < 500ms per request (target)
- **Cache Hit Rate**: > 60% (target)
- **Import Errors**: 0% (zero import errors)

### Qualitative
- Generated code uses repository-specific types
- Import statements match codebase patterns
- Function signatures follow existing conventions
- Code feels "native" to the repository

---

## Timeline

**Week 5: LSP Foundation**
- Days 1-2: Implement LSPSemanticContextProvider
- Days 3-4: Integrate with SemanticCodeGenerator
- Days 5: Testing and bug fixes

**Week 6: Validation and Polish**
- Days 1-2: Quality validation experiments
- Days 3-4: Performance optimization
- Days 5: Documentation and demo

**Total**: 10 working days

---

## Dependencies

### Python Packages
```toml
[project.dependencies]
multilspy = "^1.0.0"
pyright = "^1.1.300"
```

### External Tools
- **pyright**: Python language server (installed via npm or pip)
- **Node.js**: Required for pyright (if installed via npm)

### Optional
- **rust-analyzer**: For Rust support
- **typescript-language-server**: For TypeScript support
- **gopls**: For Go support

---

## References

- **multilspy**: https://github.com/microsoft/multilspy
- **LSP Specification**: https://microsoft.github.io/language-server-protocol/
- **pyright**: https://github.com/microsoft/pyright
- **INTEGRATION_ROADMAP.md**: Week 5-6 section
- **PoC 2 Results**: 1.17x average, 1.58x peak improvement

---

**End of LSP Integration Design**
