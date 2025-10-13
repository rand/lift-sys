# Reverse Mode: Specification Extraction from Existing Code

Reverse mode is lift-sys's capability for extracting formal specifications from existing codebases. It uses static and dynamic analysis tools to recover behavioral models, security properties, and invariants from production code.

## Overview

### What is Reverse Mode?

Reverse mode analyzes existing code to:
- Extract function signatures, types, and parameters
- Identify security vulnerabilities using CodeQL
- Discover runtime invariants using Daikon
- Infer API relationships using stack graphs
- Generate formal specifications in IR format

### When to Use Reverse Mode

- **Legacy Code Documentation**: Generate specifications for undocumented code
- **Code Understanding**: Quickly understand what a codebase does
- **Refactoring Safety**: Extract contracts before modifying code
- **Security Audits**: Identify potential vulnerabilities
- **Migration Planning**: Understand dependencies before porting code

## Analysis Modes

### Project Mode (Whole-Project Analysis)

Analyzes all Python files in a repository in a single operation.

**Benefits:**
- Comprehensive understanding of entire codebase
- Batch processing for efficiency
- Cross-file relationship analysis
- Progress tracking for long-running analyses

**Best for:**
- Initial codebase assessment
- Security audits
- Documentation generation
- Understanding project architecture

**Example:**
```python
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

config = LifterConfig(
    codeql_queries=["security/default"],
    run_codeql=True,
    run_daikon=False  # Disable for faster analysis
)
lifter = SpecificationLifter(config)
lifter.load_repository("/path/to/repo")

# Analyze all files
irs = lifter.lift_all(max_files=50)  # Limit to first 50 files

print(f"Analyzed {len(irs)} files")
for ir in irs:
    print(f"  - {ir.metadata.source_path}: {ir.signature.name}")
```

### File Mode (Single-File Analysis)

Focuses analysis on a specific module.

**Benefits:**
- Faster analysis
- Targeted investigation
- Lower resource usage
- Immediate results

**Best for:**
- Understanding specific functions
- Debugging specific modules
- Incremental analysis
- API endpoint analysis

**Example:**
```python
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

config = LifterConfig(
    codeql_queries=["security/default"],
    daikon_entrypoint="main",
    run_codeql=True,
    run_daikon=True
)
lifter = SpecificationLifter(config)
lifter.load_repository("/path/to/repo")

# Analyze single file
ir = lifter.lift("src/api/auth.py")

print(f"Function: {ir.signature.name}")
print(f"Intent: {ir.intent.summary}")
print(f"Assertions: {len(ir.assertions)}")
```

## API Endpoints

### POST /api/reverse

Triggers reverse mode analysis.

**Request Body:**
```json
{
  "module": null | "path/to/file.py",
  "analyze_all": true | false,
  "queries": ["security/default"],
  "entrypoint": "main"
}
```

**Parameters:**
- `module`: File path for single-file mode, `null` for project mode
- `analyze_all`: Set to `true` for project mode (default: `true`)
- `queries`: CodeQL queries to run (e.g., `["security/default"]`)
- `entrypoint`: Entry function for dynamic analysis (e.g., `"main"`)

**Response:**
```json
{
  "irs": [
    {
      "intent": {
        "summary": "Validates user authentication tokens",
        "rationale": "Derived from static analysis",
        "holes": []
      },
      "signature": {
        "name": "validate_token",
        "parameters": [
          {"name": "token", "type_hint": "str", "description": "JWT token"}
        ],
        "returns": "bool"
      },
      "effects": [
        {"description": "Reads external API"}
      ],
      "assertions": [
        {
          "predicate": "token is not None",
          "rationale": "Token must be provided"
        }
      ],
      "metadata": {
        "source_path": "src/api/auth.py",
        "origin": "reverse",
        "language": "python",
        "evidence": [
          {
            "id": "codeql-0",
            "analysis": "codeql",
            "location": "src/api/auth.py:45",
            "message": "Potential SQL injection",
            "metadata": {}
          }
        ]
      }
    }
  ],
  "progress": []
}
```

### WebSocket: Progress Updates

When running project mode, the API sends real-time progress via WebSocket at `/ws`.

**Progress Event Format:**
```json
{
  "type": "progress",
  "scope": "reverse",
  "stage": "file_analysis",
  "status": "running",
  "message": "Analyzing src/utils.py (5/20)",
  "current": 5,
  "total": 20,
  "file": "src/utils.py"
}
```

**Stages:**
- `file_discovery`: Finding Python files
- `file_analysis`: Analyzing individual files
- `codeql`: Running CodeQL analysis
- `daikon`: Running Daikon analysis

## Web UI Workflow

### Step 1: Navigate to Repository View

1. Open http://localhost:5173
2. Click "Repository" in the sidebar
3. Select or connect a repository

### Step 2: Choose Analysis Mode

Two mode buttons are available:
- **Entire Project**: Analyzes all Python files
- **Single File**: Analyzes a specific module

### Step 3: Configure Analysis (File Mode Only)

For single-file analysis:
- **Module Name**: Enter the file path (e.g., `src/utils.py`)
- **Entrypoint**: Entry function for dynamic analysis (e.g., `main`)

For project mode, these inputs are hidden.

### Step 4: Run Analysis

Click "Analyze" to start the analysis. You'll see:
- Progress bar showing current file and completion percentage
- Real-time updates as files are processed
- Estimated time remaining

### Step 5: View Results

**Results Overview:**
- List of all analyzed files
- Summary statistics (files analyzed, holes found, assertions)
- Search bar to filter results by filename or content
- Each result shows:
  - File path
  - Function name
  - Summary
  - Number of holes and assertions

**Detailed View:**
Click "View Details" on any file to see:
- Complete function signature with types
- Intent summary and rationale
- Effects on external systems
- Assertions and invariants
- Typed holes requiring human input
- Evidence from analysis tools
- Metadata (origin, language, source path)

**Navigation:**
- "Back to Results" returns to the overview
- Search persists across navigation
- Results remain available until next analysis

## Configuration

### LifterConfig Options

```python
from lift_sys.reverse_mode.lifter import LifterConfig

config = LifterConfig(
    # CodeQL configuration
    codeql_queries=["security/default"],
    run_codeql=True,

    # Daikon configuration
    daikon_entrypoint="main",
    run_daikon=True,

    # Stack graphs configuration
    stack_index_path="/path/to/index",
    run_stack_graphs=False
)
```

**Parameters:**
- `codeql_queries`: List of CodeQL query suites to run
- `run_codeql`: Enable/disable CodeQL analysis (default: `True`)
- `daikon_entrypoint`: Entry function for Daikon traces (default: `"main"`)
- `run_daikon`: Enable/disable Daikon analysis (default: `True`)
- `stack_index_path`: Path to stack graphs index
- `run_stack_graphs`: Enable/disable stack graphs (default: `True`)

### File Discovery

By default, reverse mode discovers all `.py` files while excluding:
- `venv`, `.venv` (virtual environments)
- `node_modules` (JavaScript dependencies)
- `__pycache__`, `.pytest_cache`, `.mypy_cache` (caches)
- `.git`, `.tox`, `.eggs` (build/version control)
- `build`, `dist`, `.egg-info` (build artifacts)
- `htmlcov` (coverage reports)

**Custom Exclusions:**
```python
lifter.discover_python_files(
    exclude_patterns=["tests/*", "migrations/*", "scripts/*"]
)
```

## Advanced Features

### Progress Callbacks

Track analysis progress programmatically:

```python
def progress_handler(file_path: str, current: int, total: int):
    percent = (current / total) * 100
    print(f"[{percent:.1f}%] Analyzing {file_path} ({current}/{total})")

irs = lifter.lift_all(progress_callback=progress_handler)
```

### Error Handling

Analysis continues even if individual files fail:

```python
irs = lifter.lift_all()

# Check progress log for errors
if lifter.progress_log:
    errors = [log for log in lifter.progress_log if "error:" in log]
    if errors:
        print(f"Encountered {len(errors)} errors:")
        for error in errors:
            print(f"  {error}")

print(f"Successfully analyzed {len(irs)} files")
```

### Limiting Analysis

For large codebases, limit the number of files:

```python
# Analyze only first 100 files
irs = lifter.lift_all(max_files=100)
```

### Metadata and Evidence

Each IR includes evidence from analysis tools:

```python
ir = lifter.lift("src/utils.py")

# Access evidence
for evidence in ir.metadata.evidence:
    print(f"Evidence ID: {evidence['id']}")
    print(f"Analysis: {evidence['analysis']}")
    print(f"Location: {evidence['location']}")
    print(f"Message: {evidence['message']}")
```

## Performance Considerations

### Analysis Speed

Typical analysis times (on a MacBook Pro M1):
- **Single file**: 5-10 seconds
- **Small project** (10-50 files): 1-5 minutes
- **Medium project** (50-200 files): 5-20 minutes
- **Large project** (200+ files): 20+ minutes

### Optimization Tips

1. **Disable unused analyzers:**
   ```python
   config = LifterConfig(
       run_codeql=True,
       run_daikon=False,  # Disable if not needed
       run_stack_graphs=False
   )
   ```

2. **Limit file count:**
   ```python
   irs = lifter.lift_all(max_files=50)  # Analyze subset
   ```

3. **Use file mode for targeted analysis:**
   ```python
   # Faster than analyzing entire project
   ir = lifter.lift("src/critical_module.py")
   ```

4. **Exclude test files:**
   ```python
   files = lifter.discover_python_files(
       exclude_patterns=["tests/*", "test_*.py", "*_test.py"]
   )
   ```

## Troubleshooting

### Common Issues

**Issue: "Repository not loaded"**
```python
# Ensure you call load_repository before analysis
lifter.load_repository("/path/to/repo")
```

**Issue: No files discovered**
```python
# Check exclusion patterns
files = lifter.discover_python_files()
print(f"Found {len(files)} Python files")
```

**Issue: Analysis fails silently**
```python
# Check progress log for errors
print(lifter.progress_log)
```

**Issue: CodeQL not found**
```bash
# Install CodeQL CLI
# See: https://codeql.github.com/docs/codeql-cli/
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

lifter = SpecificationLifter(config)
# Now see detailed logs during analysis
```

## Integration Examples

### CI/CD Pipeline

```bash
#!/bin/bash
# ci-analyze-code.sh

# Analyze codebase and save results
curl -X POST http://localhost:8000/api/reverse \
  -H "Content-Type: application/json" \
  -d '{
    "module": null,
    "analyze_all": true,
    "queries": ["security/default"]
  }' | jq '.irs' > analysis-results.json

# Check for security findings
SECURITY_ISSUES=$(jq '[.[] | select(.metadata.evidence[] | .analysis == "codeql")] | length' analysis-results.json)

if [ "$SECURITY_ISSUES" -gt 0 ]; then
  echo "Found $SECURITY_ISSUES security issues"
  exit 1
fi
```

### Pre-commit Hook

```python
#!/usr/bin/env python3
# .git/hooks/pre-commit
import sys
from lift_sys.reverse_mode.lifter import SpecificationLifter, LifterConfig

config = LifterConfig(run_daikon=False)  # Fast analysis
lifter = SpecificationLifter(config)
lifter.load_repository(".")

# Get staged files
import subprocess
result = subprocess.run(
    ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
    capture_output=True, text=True
)
staged_files = [f for f in result.stdout.splitlines() if f.endswith(".py")]

# Analyze staged files
for file_path in staged_files:
    try:
        ir = lifter.lift(file_path)
        # Check for security issues in evidence
        security_issues = [
            e for e in ir.metadata.evidence
            if e.get("analysis") == "codeql"
        ]
        if security_issues:
            print(f"Security issues in {file_path}:")
            for issue in security_issues:
                print(f"  - {issue['message']}")
            sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")

print("All staged files passed reverse mode analysis")
```

## Best Practices

1. **Start with project mode** for initial understanding
2. **Use file mode** for deep dives into specific areas
3. **Disable unused analyzers** for faster results
4. **Check progress logs** to understand what was analyzed
5. **Save IRs** for future reference and comparison
6. **Combine with forward mode** for refactoring workflows

## Related Documentation

- [Performance Guide](PERFORMANCE.md) - Benchmarks, optimization, and resource planning
- [API Session Management](API_SESSION_MANAGEMENT.md) - Forward mode documentation
- [Workflow Guides](WORKFLOW_GUIDES.md) - Complete usage examples
- [FAQ](FAQ.md) - Common questions and answers
