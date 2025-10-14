# Week 7-8: TypeScript Multi-Language Support - Implementation Plan

**Version**: 1.0
**Date**: October 14, 2025
**Status**: Planning
**bd Issue**: lift-sys-52
**Dependencies**: Week 5-6 LSP Integration (lift-sys-51) ✅ COMPLETE

---

## Executive Summary

Extend lift-sys to support TypeScript code generation and analysis by leveraging the production-ready LSP optimization system built in Week 6. This phase validates the language-agnostic architecture and establishes patterns for future language additions (Rust, Go).

**Timeline**: 2-3 weeks
**Success Criteria**: 90%+ test pass rate, 100% syntax validity, zero import errors

---

## Goals

### Primary Goals
1. ✅ Add TypeScript type grammar to xgrammar
2. ✅ Configure `typescript-language-server` for LSP
3. ✅ Implement TypeScript-specific code generator
4. ✅ Test with TypeScript IRs
5. ✅ Verify syntax validity and semantic correctness
6. ✅ Document TypeScript support

### Success Metrics
- **Syntax Validity**: 100% (xgrammar guarantee)
- **Test Pass Rate**: 90%+ for TypeScript generation
- **Import Accuracy**: 0 import errors with LSP context
- **Quality Improvement**: 1.3-1.5x with LSP (same as Python)
- **Cache Performance**: 60-70% hit rate (reuse Week 6 optimization)
- **Generation Latency**: <2s per function

---

## Phase Breakdown

### Phase 1: TypeScript Grammar and Type System (Days 1-3)

**Goal**: Establish TypeScript grammar and type resolution

**Tasks**:
- [ ] Research xgrammar TypeScript support
  - Check if xgrammar has built-in TypeScript grammar
  - Review TypeScript AST structure vs Python
  - Identify differences: interfaces, type aliases, generics, union types

- [ ] Create TypeScript type grammar
  - Define TypeScript-specific type constructs
  - Handle interfaces, type aliases, enum types
  - Support TypeScript generics (`Array<T>`, `Promise<T>`)
  - Handle union types (`string | number`)
  - Support literal types and mapped types

- [ ] Implement TypeScript type resolver
  - Create `TypeScriptTypeResolver` class
  - Map IR types to TypeScript types
  - Handle TypeScript-specific type annotations
  - Support import type syntax (`import type { Foo } from 'bar'`)

- [ ] Write unit tests for type resolution
  - Test basic types: string, number, boolean, array
  - Test complex types: interfaces, generics, unions
  - Test import type statements
  - Test type inference for parameters

**Deliverables**:
- `lift_sys/codegen/languages/typescript_types.py` - Type resolution
- `lift_sys/codegen/grammars/typescript.json` - xgrammar grammar (if needed)
- `tests/unit/test_typescript_types.py` - 15+ type resolution tests

**Success Criteria**:
- All TypeScript type constructs mapped correctly
- 15+ type resolution tests passing
- Type grammar validated with xgrammar

---

### Phase 2: TypeScript LSP Integration (Days 4-6)

**Goal**: Configure and test `typescript-language-server` with existing LSP optimization

**Tasks**:
- [ ] Install and configure typescript-language-server
  - Install via npm: `npm install -g typescript-language-server`
  - Install TypeScript: `npm install -g typescript`
  - Test server startup and capabilities
  - Configure server initialization options

- [ ] Extend LSPSemanticContextProvider for TypeScript
  - Add TypeScript language detection
  - Configure multilspy for TypeScript
  - Test document symbol queries
  - Test completion and hover queries
  - Verify semantic context retrieval

- [ ] Apply Week 6 optimizations to TypeScript
  - Verify LSP caching works for TypeScript files
  - Test smart file discovery with .ts/.tsx files
  - Validate parallel queries for multiple TypeScript files
  - Apply relevance ranking to TypeScript symbols
  - Ensure metrics collection works for TypeScript

- [ ] Test LSP integration with real TypeScript repositories
  - Use popular TypeScript project (e.g., VSCode, TypeScript compiler)
  - Verify symbol retrieval accuracy
  - Measure cache hit rates
  - Validate context relevance

**Deliverables**:
- `lift_sys/codegen/lsp_config.py` - Updated with TypeScript config
- `tests/integration/test_typescript_lsp.py` - TypeScript LSP tests
- Documentation: TypeScript LSP setup guide

**Success Criteria**:
- typescript-language-server starts and stops cleanly
- Can retrieve types, functions, interfaces from TypeScript code
- Cache hit rate: 60-70% (same as Python)
- Context relevance: 70%+ symbols used

---

### Phase 3: TypeScript Code Generation (Days 7-10)

**Goal**: Implement TypeScript code generator with xgrammar

**Tasks**:
- [ ] Create TypeScript code generator class
  - Extend base `XGrammarCodeGenerator`
  - Implement TypeScript-specific generation
  - Handle TypeScript syntax: `const`, `let`, arrow functions
  - Support TypeScript module syntax (`export`, `import`)
  - Generate TypeScript interfaces/types when needed

- [ ] Implement TypeScript-specific code patterns
  - Arrow function generation: `const foo = (x: number) => x * 2`
  - Async/await syntax: `async function foo(): Promise<T>`
  - Interface definitions: `interface User { name: string; age: number; }`
  - Type guards: `if (typeof x === 'string')`
  - Null safety: `x?.property` and `x ?? defaultValue`

- [ ] Integrate with LSP semantic context
  - Use TypeScript symbols from LSP
  - Generate correct import statements
  - Use repository-specific types and interfaces
  - Follow TypeScript conventions from codebase

- [ ] Implement assertion injection for TypeScript
  - TypeScript assertion syntax
  - Runtime validation with type guards
  - Optional: Integration with io-ts or zod for runtime validation

- [ ] Add docstring generation for TypeScript
  - TSDoc format: `/** ... */`
  - Parameter documentation: `@param`
  - Return documentation: `@returns`
  - Example usage: `@example`

**Deliverables**:
- `lift_sys/codegen/languages/typescript_generator.py` - Code generator
- `lift_sys/codegen/typescript_schema.py` - TypeScript code schema
- `tests/integration/test_typescript_generation.py` - 10+ generation tests

**Success Criteria**:
- 100% syntactically valid TypeScript code
- Can compile with `tsc --noEmit`
- Uses correct types and imports with LSP
- 10+ test IRs generate successfully

---

### Phase 4: Testing and Quality Validation (Days 11-12)

**Goal**: Validate TypeScript generation quality and performance

**Tasks**:
- [ ] Create TypeScript test suite
  - 20 test prompts covering common patterns
  - File I/O operations
  - API interactions
  - Data transformation
  - Async operations
  - Type-safe utilities

- [ ] Run quality validation experiments
  - Baseline: TypeScript generation without LSP
  - Enhanced: TypeScript generation with LSP context
  - Measure quality improvement (target: 1.3-1.5x)
  - Compare to Python results (1.30x average)

- [ ] Test with real TypeScript repositories
  - Generate functions for existing TypeScript codebases
  - Verify imports match project structure
  - Validate types match repository conventions
  - Check that generated code passes linting (ESLint)

- [ ] Performance benchmarking
  - Measure generation latency
  - Verify cache effectiveness
  - Test parallel query performance
  - Compare to Python baseline

- [ ] Syntax validation
  - Compile all generated code with `tsc`
  - Verify 100% syntax validity
  - Check type correctness
  - Validate runtime behavior

**Deliverables**:
- `experiments/validate_typescript_quality.py` - Quality validation
- `experiments/benchmark_typescript_generation.py` - Performance tests
- TypeScript test suite with 20+ test cases
- Quality metrics report

**Success Criteria**:
- 100% syntax validity (20/20 test cases)
- 90%+ test pass rate
- Quality improvement: 1.3-1.5x with LSP
- Generation latency: <2s per function

---

### Phase 5: Documentation and Integration (Days 13-14)

**Goal**: Document TypeScript support and prepare for production

**Tasks**:
- [ ] Write TypeScript support documentation
  - Getting started with TypeScript generation
  - TypeScript-specific features and patterns
  - LSP configuration for TypeScript projects
  - Troubleshooting guide

- [ ] Update API documentation
  - Add TypeScript language option to API
  - Document TypeScript-specific parameters
  - Provide API examples for TypeScript

- [ ] Create TypeScript examples
  - Example TypeScript IRs
  - Generated TypeScript code samples
  - Real-world use cases

- [ ] Update CLI and UI
  - Add TypeScript language selector
  - Update configuration views
  - Add TypeScript syntax highlighting

- [ ] Integration testing
  - End-to-end: Prompt → IR → TypeScript code
  - Test with multiple TypeScript frameworks (React, Node.js, Deno)
  - Verify multi-language switching (Python ↔ TypeScript)

**Deliverables**:
- `docs/TYPESCRIPT_SUPPORT.md` - Complete TypeScript guide
- `examples/typescript/` - Example TypeScript generation
- Updated API documentation
- E2E test suite for TypeScript

**Success Criteria**:
- Complete documentation for TypeScript support
- 5+ TypeScript examples working
- E2E tests passing for TypeScript workflow
- Language switching working seamlessly

---

## Technical Architecture

### Language Abstraction Layer

```python
# File: lift_sys/codegen/language_factory.py

from abc import ABC, abstractmethod
from typing import Protocol

class LanguageGenerator(Protocol):
    """Protocol for language-specific code generators."""

    language: str

    @abstractmethod
    async def generate_function(self, ir: IR) -> GeneratedCode:
        """Generate code from IR."""
        ...

    @abstractmethod
    def resolve_type(self, type_hint: str) -> TypeAnnotation:
        """Resolve IR type to language-specific type."""
        ...

    @abstractmethod
    def format_code(self, code: str) -> str:
        """Format code using language-specific formatter."""
        ...


class LanguageFactory:
    """Factory for creating language-specific generators."""

    @staticmethod
    def create_generator(
        language: str,
        repository_path: Path | None = None,
    ) -> LanguageGenerator:
        """Create generator for specified language."""
        if language == "python":
            from .languages.python_generator import PythonGenerator
            return PythonGenerator(repository_path)

        elif language == "typescript":
            from .languages.typescript_generator import TypeScriptGenerator
            return TypeScriptGenerator(repository_path)

        elif language == "rust":
            from .languages.rust_generator import RustGenerator
            return RustGenerator(repository_path)

        elif language == "go":
            from .languages.go_generator import GoGenerator
            return GoGenerator(repository_path)

        else:
            raise ValueError(f"Unsupported language: {language}")
```

### TypeScript Generator Structure

```python
# File: lift_sys/codegen/languages/typescript_generator.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..xgrammar_generator import XGrammarCodeGenerator
from ..lsp_context import LSPSemanticContextProvider, LSPConfig
from .typescript_types import TypeScriptTypeResolver

class TypeScriptGenerator(XGrammarCodeGenerator):
    """TypeScript code generator with LSP optimization."""

    language = "typescript"

    def __init__(
        self,
        provider: BaseProvider,
        repository_path: Path | None = None,
        config: CodeGeneratorConfig | None = None,
    ):
        """Initialize TypeScript generator."""
        super().__init__(provider, config)

        # TypeScript-specific type resolver
        self.type_resolver = TypeScriptTypeResolver()

        # LSP context provider for TypeScript
        if repository_path:
            lsp_config = LSPConfig(
                repository_path=repository_path,
                language="typescript",
                cache_enabled=True,
                metrics_enabled=True,
            )
            self.context_provider = LSPSemanticContextProvider(lsp_config)
        else:
            # Fallback to knowledge base
            from ..semantic_context import SemanticContextProvider
            self.context_provider = SemanticContextProvider(language="typescript")

    def _get_language_grammar(self) -> str:
        """Get TypeScript grammar for xgrammar."""
        # Use xgrammar built-in TypeScript grammar if available
        # Otherwise load custom grammar
        return "typescript"

    def _format_code(self, code: str) -> str:
        """Format TypeScript code using prettier."""
        import subprocess
        try:
            result = subprocess.run(
                ["npx", "prettier", "--parser", "typescript"],
                input=code.encode(),
                capture_output=True,
                timeout=5,
            )
            return result.stdout.decode()
        except Exception:
            # Fallback: return unformatted code
            return code

    def _build_generation_prompt(
        self,
        ir: IR,
        semantic_context: SemanticContext | None = None,
    ) -> str:
        """Build TypeScript-specific generation prompt."""
        prompt_parts = []

        # Intent
        prompt_parts.append(f"// {ir.intent.summary}")
        if ir.intent.rationale:
            prompt_parts.append(f"// {ir.intent.rationale}")

        # Function signature with TypeScript syntax
        params = ", ".join(
            f"{p.name}: {self.type_resolver.resolve(p.type_hint).annotation}"
            for p in ir.signature.parameters
        )
        return_type = self.type_resolver.resolve(ir.signature.returns).annotation

        prompt_parts.append(
            f"export function {ir.signature.name}({params}): {return_type} {{"
        )

        # Semantic context if available
        if semantic_context:
            prompt_parts.append("// Available types from codebase:")
            for type_info in semantic_context.available_types[:3]:
                prompt_parts.append(f"// - {type_info.name}: {type_info.description}")

        # Body placeholder
        prompt_parts.append("  // TODO: Implementation")
        prompt_parts.append("}")

        return "\n".join(prompt_parts)
```

---

## Dependencies

### External Tools
- **typescript-language-server**: npm install -g typescript-language-server
- **typescript**: npm install -g typescript (peer dependency)
- **prettier** (optional): npm install -g prettier (for code formatting)
- **eslint** (optional): For code quality validation

### Python Packages
- **xgrammar**: Already installed ✅
- **multilspy**: Already installed ✅
- All Week 6 LSP optimization components ✅

### Internal Dependencies
- Week 5-6 LSP optimization system (lift-sys-51) ✅ COMPLETE
- xgrammar code generation (Week 3-4) ✅ COMPLETE
- IR data model ✅ COMPLETE

---

## Testing Strategy

### Unit Tests (30+ tests)
1. **Type Resolution** (15 tests)
   - Basic types: string, number, boolean
   - Complex types: interfaces, generics, unions
   - Import type statements
   - Type guards and narrowing

2. **LSP Integration** (10 tests)
   - TypeScript language server startup
   - Symbol retrieval from .ts files
   - Completion context for TypeScript
   - Cache behavior with TypeScript

3. **Code Generation** (5 tests)
   - Function generation
   - Interface generation
   - Import statement generation
   - Docstring generation (TSDoc)

### Integration Tests (15+ tests)
1. **End-to-End Generation** (10 tests)
   - Prompt → IR → TypeScript code
   - With LSP context (repository-specific)
   - Without LSP context (baseline)
   - Multi-file TypeScript projects

2. **Quality Validation** (5 tests)
   - Syntax validity (tsc compilation)
   - Import accuracy
   - Type correctness
   - Runtime behavior

### Performance Tests (5+ tests)
1. Cache effectiveness for TypeScript
2. Generation latency benchmarks
3. Parallel query performance
4. Memory usage with multiple TypeScript files
5. Language switching overhead (Python ↔ TypeScript)

**Total Tests**: 50+ (30 unit + 15 integration + 5 performance)

---

## Risk Assessment

### Technical Risks

**Risk 1: TypeScript Type System Complexity** (Probability: Medium, Impact: Medium)
- **Description**: TypeScript's advanced type system (conditional types, mapped types) may be challenging
- **Mitigation**: Start with basic types, incrementally add advanced features
- **Contingency**: Generate code with `any` types if resolution fails, add TODO comments

**Risk 2: typescript-language-server Configuration** (Probability: Low, Impact: Medium)
- **Description**: LSP server may require project-specific configuration (tsconfig.json)
- **Mitigation**: Use reasonable defaults, auto-detect tsconfig.json when present
- **Contingency**: Fall back to knowledge base without LSP if server fails

**Risk 3: xgrammar TypeScript Support** (Probability: Low, Impact: High)
- **Description**: xgrammar may not have robust TypeScript grammar support
- **Mitigation**: Test xgrammar TypeScript support early (Day 1), use built-in if available
- **Contingency**: Create custom TypeScript grammar, or use llguidance for TypeScript

**Risk 4: npm Dependencies** (Probability: Low, Impact: Low)
- **Description**: Requiring npm for language server adds deployment complexity
- **Mitigation**: Document npm installation, provide Docker container with dependencies
- **Contingency**: Package typescript-language-server in deployment

---

## Success Criteria Summary

### Must Have (P0)
- ✅ 100% syntax validity for generated TypeScript code
- ✅ 90%+ test pass rate (compilation + runtime)
- ✅ 0 import errors with LSP context
- ✅ TypeScript language server integration working
- ✅ 50+ tests passing (30 unit + 15 integration + 5 performance)

### Should Have (P1)
- ✅ 1.3-1.5x quality improvement with LSP (same as Python)
- ✅ <2s generation latency per function
- ✅ 60-70% cache hit rate
- ✅ Complete documentation and examples

### Nice to Have (P2)
- Integration with TypeScript frameworks (React, Node.js)
- Advanced type inference and type guards
- Integration with io-ts or zod for runtime validation
- ESLint integration for code quality

---

## Deliverables Checklist

### Code
- [ ] `lift_sys/codegen/languages/typescript_generator.py`
- [ ] `lift_sys/codegen/languages/typescript_types.py`
- [ ] `lift_sys/codegen/language_factory.py`
- [ ] `lift_sys/codegen/grammars/typescript.json` (if needed)

### Tests
- [ ] `tests/unit/test_typescript_types.py` (15 tests)
- [ ] `tests/unit/test_typescript_generation.py` (5 tests)
- [ ] `tests/integration/test_typescript_lsp.py` (10 tests)
- [ ] `tests/integration/test_typescript_generation.py` (10 tests)
- [ ] `tests/performance/test_typescript_performance.py` (5 tests)

### Documentation
- [ ] `docs/TYPESCRIPT_SUPPORT.md`
- [ ] `docs/LANGUAGE_EXTENSION_GUIDE.md`
- [ ] Update `docs/LSP_INTEGRATION_DESIGN.md` with TypeScript
- [ ] Update `README.md` with TypeScript examples

### Experiments
- [ ] `experiments/validate_typescript_quality.py`
- [ ] `experiments/benchmark_typescript_generation.py`
- [ ] `examples/typescript/` - 5+ examples

### Integration
- [ ] Update API to accept `language="typescript"`
- [ ] Update CLI with TypeScript option
- [ ] Update UI with TypeScript selector
- [ ] Add TypeScript syntax highlighting

---

## Timeline

### Week 7 (Days 1-7)
- **Days 1-3**: Phase 1 - TypeScript grammar and type system
- **Days 4-6**: Phase 2 - TypeScript LSP integration
- **Day 7**: Phase 3 start - Code generator class

### Week 8 (Days 8-14)
- **Days 8-10**: Phase 3 - Complete TypeScript code generation
- **Days 11-12**: Phase 4 - Testing and quality validation
- **Days 13-14**: Phase 5 - Documentation and integration

**Total**: 14 days (2 weeks)

---

## Next Steps

### Immediate (This Week)
1. Research xgrammar TypeScript support
2. Install typescript-language-server locally
3. Test LSP server with sample TypeScript project
4. Review TypeScript type system differences vs Python

### Week 7 Day 1 (Monday)
1. Create TypeScript type resolver
2. Implement basic type mapping
3. Write first 5 type resolution tests
4. Validate approach with xgrammar

### Week 7 Day 2 (Tuesday)
1. Complete type resolver (interfaces, generics, unions)
2. Finish all 15 type resolution tests
3. Test xgrammar TypeScript grammar
4. Begin LSP configuration

---

## References

- **Week 5-6 Results**: All LSP optimization components ready for reuse
- **xgrammar TypeScript**: https://github.com/mlc-ai/xgrammar (check TypeScript support)
- **typescript-language-server**: https://github.com/typescript-language-server/typescript-language-server
- **TypeScript Handbook**: https://www.typescriptlang.org/docs/handbook/intro.html
- **TSDoc**: https://tsdoc.org/ (docstring format)
- **multilspy TypeScript**: Check multilspy docs for TypeScript configuration

---

**End of Week 7-8 TypeScript Plan**
