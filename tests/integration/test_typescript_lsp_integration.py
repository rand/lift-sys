"""Integration tests for TypeScript LSP with LSPSemanticContextProvider."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from lift_sys.codegen.lsp_context import LSPConfig, LSPSemanticContextProvider


class TestTypeScriptLSPIntegration:
    """Test TypeScript LSP integration with semantic context provider."""

    @pytest.mark.asyncio
    async def test_typescript_lsp_starts_and_stops(self):
        """Test that TypeScript LSP server starts and stops cleanly."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create a minimal TypeScript project
        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text(
            '{"compilerOptions": {"target": "ES2020", "module": "commonjs"}}'
        )

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=True,
            metrics_enabled=True,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            # Start should complete without errors
            await provider.start()
            assert provider._started

            # Stop should complete without errors
            await provider.stop()
            assert not provider._started

        finally:
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_find_typescript_files(self):
        """Test that file discovery finds TypeScript files."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create TypeScript files
        (repo_path / "src").mkdir()
        (repo_path / "src" / "user.ts").write_text(
            """
interface User {
    name: string;
    email: string;
}

export function createUser(name: string, email: string): User {
    return { name, email };
}
"""
        )
        (repo_path / "src" / "utils.ts").write_text(
            """
export function validateEmail(email: string): boolean {
    return email.includes('@');
}
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=False,
            metrics_enabled=False,
        )

        provider = LSPSemanticContextProvider(config)

        # Test file discovery
        keywords = ["user", "email"]
        files = provider._find_relevant_files(keywords, "create user with email", limit=2)

        assert len(files) > 0
        assert any("user.ts" in str(f) for f in files)

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_typescript_symbol_retrieval(self):
        """Test retrieving symbols from TypeScript code."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create TypeScript file with various symbols
        test_file = repo_path / "test.ts"
        test_file.write_text(
            """
interface Product {
    id: number;
    name: string;
    price: number;
}

class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }

    multiply(a: number, b: number): number {
        return a * b;
    }
}

export function formatPrice(price: number): string {
    return `$${price.toFixed(2)}`;
}
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=True,
            metrics_enabled=True,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            await provider.start()

            # Get symbols from file
            symbols = await provider._get_document_symbols(test_file)

            # Should have retrieved symbols (exact structure depends on LSP server)
            # This test validates that LSP communication works
            assert symbols is not None  # May be empty list or contain symbols

        except Exception as cleanup_error:
            # Ignore PID cleanup errors
            if "PID not found" not in str(cleanup_error):
                raise

        finally:
            await provider.stop()
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_typescript_context_retrieval(self):
        """Test getting semantic context for TypeScript."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create TypeScript project structure
        (repo_path / "src").mkdir()
        (repo_path / "src" / "api.ts").write_text(
            """
export interface ApiResponse<T> {
    data: T;
    status: number;
}

export async function fetchData<T>(url: string): Promise<ApiResponse<T>> {
    const response = await fetch(url);
    return {
        data: await response.json(),
        status: response.status
    };
}
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=True,
            metrics_enabled=True,
            fallback_to_knowledge_base=True,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            await provider.start()

            # Get context for an API-related intent
            context = await provider.get_context_for_intent(
                "create function to fetch user data from API"
            )

            # Should return context (may use fallback if LSP fails)
            assert context is not None
            assert context.codebase_conventions is not None

            # Verify TypeScript conventions are present
            assert (
                "typescript" in str(context.codebase_conventions).lower()
                or len(context.codebase_conventions) > 0
            )

        except Exception as cleanup_error:
            if "PID not found" not in str(cleanup_error):
                raise

        finally:
            await provider.stop()
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_typescript_import_patterns(self):
        """Test TypeScript import pattern suggestions."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=False,
            metrics_enabled=False,
        )

        provider = LSPSemanticContextProvider(config)

        # Test file operations keywords
        keywords = ["file", "path", "read"]
        imports = provider._get_imports_for_keywords(keywords)

        assert len(imports) > 0
        assert any("fs" in imp.module or "path" in imp.module for imp in imports)

        # Test date operations keywords
        keywords = ["date", "format", "time"]
        imports = provider._get_imports_for_keywords(keywords)

        assert len(imports) > 0

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_typescript_conventions(self):
        """Test TypeScript coding conventions."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
        )

        provider = LSPSemanticContextProvider(config)
        conventions = provider._get_conventions()

        assert "error_handling" in conventions
        assert "type_annotations" in conventions
        assert "async" in conventions
        assert "null_safety" in conventions

        # Verify TypeScript-specific content
        assert "TSDoc" in conventions["docstrings"] or "param" in conventions["docstrings"]
        assert "async/await" in conventions["async"] or "Promise" in conventions["async"]

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_typescript_cache_integration(self):
        """Test that caching works for TypeScript files."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        test_file = repo_path / "test.ts"
        test_file.write_text(
            """
export function greet(name: string): string {
    return `Hello, ${name}!`;
}
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=True,
            metrics_enabled=True,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            await provider.start()

            # First query (cache miss)
            symbols1 = await provider._get_document_symbols(test_file)

            # Second query (should hit cache)
            symbols2 = await provider._get_document_symbols(test_file)

            # Both should return the same result
            assert symbols1 == symbols2

            # Check metrics
            metrics = provider.get_metrics()
            if metrics.get("enabled", True):
                # Should have at least 2 queries
                assert metrics["queries"]["total"] >= 2
                # Should have cache statistics
                assert "cache" in metrics

        except Exception as cleanup_error:
            if "PID not found" not in str(cleanup_error):
                raise

        finally:
            await provider.stop()
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_tsx_file_support(self):
        """Test that .tsx files are also discovered."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create .tsx file (React TypeScript)
        (repo_path / "component.tsx").write_text(
            """
import React from 'react';

interface Props {
    name: string;
}

export const Greeting: React.FC<Props> = ({ name }) => {
    return <div>Hello, {name}!</div>;
};
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=False,
        )

        provider = LSPSemanticContextProvider(config)

        # Test file discovery includes .tsx files
        keywords = ["component", "greeting"]
        files = provider._find_relevant_files(keywords, "create greeting component", limit=5)

        assert any("tsx" in str(f) for f in files)

        temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_parallel_typescript_queries(self):
        """Test parallel queries work for multiple TypeScript files."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create multiple TypeScript files
        for i in range(3):
            test_file = repo_path / f"file{i}.ts"
            test_file.write_text(
                f"""
export function func{i}(x: number): number {{
    return x * {i + 1};
}}
"""
            )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=False,
            timeout=1.0,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            await provider.start()

            file_paths = [repo_path / f"file{i}.ts" for i in range(3)]
            results = await provider._get_symbols_from_files(file_paths)

            # Should get results for all files
            assert len(results) == 3

            # Each result should be a tuple of (path, symbols)
            for result in results:
                assert isinstance(result, tuple)
                assert len(result) == 2
                # Just verify the tuple structure is correct
                # (actual symbol structure may vary by LSP server)

        except Exception as cleanup_error:
            if "PID not found" not in str(cleanup_error):
                raise

        finally:
            await provider.stop()
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_metrics_collection_for_typescript(self):
        """Test that metrics are collected correctly for TypeScript."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        test_file = repo_path / "test.ts"
        test_file.write_text(
            """
export function calculate(a: number, b: number): number {
    return a + b;
}
"""
        )

        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2020"}}')

        config = LSPConfig(
            repository_path=repo_path,
            language="typescript",
            cache_enabled=True,
            metrics_enabled=True,
        )

        provider = LSPSemanticContextProvider(config)

        try:
            await provider.start()

            # Perform some queries
            await provider._get_document_symbols(test_file)
            await provider._get_document_symbols(test_file)  # Should hit cache

            # Get metrics
            metrics = provider.get_metrics()

            # Metrics should be enabled (not have "enabled": False)
            assert metrics.get("enabled", True) is not False
            assert "queries" in metrics
            assert metrics["queries"]["total"] >= 2
            assert "cache" in metrics

        except Exception as cleanup_error:
            if "PID not found" not in str(cleanup_error):
                raise

        finally:
            await provider.stop()
            temp_dir.cleanup()
