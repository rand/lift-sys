# Repository Organization Guidelines

**Last Updated**: 2025-10-19

This document defines mandatory organization rules for maintaining a clean, navigable repository structure.

## Directory Structure

```
lift-sys/
├── docs/                    # All documentation (organized by category)
│   ├── supabase/           # Database setup and migrations
│   ├── observability/      # Monitoring and telemetry
│   ├── conjecturing/       # Conjecturing feature docs
│   ├── benchmarks/         # Performance testing results
│   ├── phases/             # Phase completion reports
│   ├── planning/           # Project planning and assessments
│   ├── fixes/              # Bug fix summaries
│   └── archive/            # Deprecated/historical docs
├── scripts/                 # Utility scripts (organized by purpose)
│   ├── benchmarks/         # Performance testing scripts
│   ├── database/           # Database utilities
│   ├── setup/              # Project setup scripts
│   └── website/            # Website maintenance
├── debug/                   # Debug data and test artifacts
├── migrations/              # Database migrations
├── tests/                   # Test suite
│   └── archive/            # Deprecated test files
└── lift_sys/               # Main Python package
```

## File Placement Rules

### ✅ DO: Keep Root Clean

**Root directory should ONLY contain:**
- `README.md` - Project overview and quick start
- `KNOWN_ISSUES.md` - Current bugs and limitations
- `RELEASE_NOTES.md` - Version history
- `SEMANTIC_IR_ROADMAP.md` - Product roadmap
- `LICENSE.md` - License information
- `CONTRIBUTING.md` - Contribution guidelines (if present)
- `pyproject.toml`, `package.json` - Package configs
- `.gitignore`, `.pre-commit-config.yaml` - VCS configs

### ❌ DON'T: Create Files in Root

**Never create in root:**
- ❌ Documentation markdown files → Use `docs/` subdirectories
- ❌ Shell scripts → Use `scripts/` subdirectories
- ❌ Python utility scripts → Use `scripts/` or `lift_sys/`
- ❌ Debug JSON files → Use `debug/`
- ❌ Temporary test files → Use `tests/archive/`
- ❌ Session/status reports → Use `docs/planning/`

## Documentation Organization

### docs/ Subdirectories

1. **docs/supabase/** - Database and Supabase
   - Setup guides, migration docs, connection troubleshooting
   - Naming: `SUPABASE_*.md`, `*_MIGRATIONS_*.md`

2. **docs/observability/** - Monitoring and telemetry
   - Honeycomb, logging, metrics, tracing
   - Naming: `HONEYCOMB_*.md`, `*_OBSERVABILITY_*.md`

3. **docs/conjecturing/** - Conjecturing feature
   - Implementation plans, research, technical specs
   - Naming: `CONJECTURING_*.md`, `*_CONJECTURING_*.md`

4. **docs/benchmarks/** - Performance testing
   - Benchmark results, calibration, regression investigations
   - Naming: `*_BENCHMARK_*.md`, `CALIBRATION_*.md`, `*_RESULTS.md`

5. **docs/phases/** - Phase completion reports
   - Phase summaries, testing reports, implementation summaries
   - Naming: `PHASE*.md`, `PHASE*_COMPLETE.md`

6. **docs/planning/** - Project planning
   - Strategic assessments, execution plans, session summaries
   - Naming: `*_PLAN_*.md`, `*_STATUS_*.md`, `*_ASSESSMENT_*.md`

7. **docs/fixes/** - Bug fixes and constraint summaries
   - Detailed fix documentation
   - Naming: `*_FIX_*.md`, `CONSTRAINT_*.md`

8. **docs/archive/** - Deprecated documentation
   - Old versions, superseded docs
   - Move here, don't delete (preserves history)

### Documentation Naming Conventions

- Use SCREAMING_SNAKE_CASE for docs: `FEATURE_DESCRIPTION.md`
- Include dates in session/status docs: `STATUS_20251019.md`
- Use descriptive prefixes: `SUPABASE_`, `HONEYCOMB_`, `PHASE_`
- Completion docs: `*_COMPLETE.md`
- Planning docs: `*_PLAN.md`, `*_PLANNING.md`

## Scripts Organization

### scripts/ Subdirectories

1. **scripts/benchmarks/** - Performance testing
   - Benchmark runners, performance analysis scripts
   - Must work from any directory (use `cd "$(dirname "$0")/../.."`)

2. **scripts/database/** - Database utilities
   - Migration runners, connection testers, backup scripts
   - Update paths when moved: `Path(__file__).parent.parent.parent / "migrations"`

3. **scripts/setup/** - Setup and initialization
   - Development environment setup, OAuth config, project startup
   - Should cd to repo root at script start

4. **scripts/website/** - Website maintenance
   - Build scripts, deploy scripts, content updaters

### Script Requirements

**All scripts must:**
1. Include shebang: `#!/bin/bash` or `#!/usr/bin/env python3`
2. Navigate to correct directory (don't assume working directory)
3. Include error handling: `set -e` for bash
4. Have descriptive comments at top
5. Be executable: `chmod +x script.sh`

**Example bash script structure:**
```bash
#!/bin/bash
# Script purpose and usage
# Run from anywhere: ./scripts/category/script.sh

set -e

# Navigate to repo root
cd "$(dirname "$0")/../.."

# Script logic here
```

**Each scripts/ subdirectory must have:**
- `README.md` with usage instructions and examples

## Debug Files Organization

### debug/ Directory

**Purpose:** Debug data, test artifacts, intermediate representations

**Contents:**
- Debug JSON files: `debug_*.json`
- Validation results: `*_validation_*.json`
- IR examples: `*_ir.json`
- Test data: `*_test_*.json`

**Rules:**
1. All debug artifacts go here, never in root
2. Add descriptive names with context
3. Update `debug/README.md` when adding new file types
4. Consider adding to `.gitignore` if files are large/temporary

## Migration Checklist

When moving existing files to match this structure:

1. **Categorize:** Determine correct subdirectory
2. **Move with git:** `git mv old_location new_location`
3. **Update paths:** Fix any internal references or script paths
4. **Update links:** Fix markdown cross-references
5. **Test:** Verify scripts still work
6. **Document:** Update README files
7. **Commit:** Clear commit message explaining organization
8. **Push:** Update remote repository

## Enforcement Rules

### When Creating New Files

**Before creating ANY new file, ask:**
1. Is this a script? → `scripts/{category}/`
2. Is this documentation? → `docs/{category}/`
3. Is this debug data? → `debug/`
4. Is this a test? → `tests/` or `tests/archive/`
5. Is this source code? → `lift_sys/` or appropriate package
6. Does it belong in root? → **Probably not!**

### Regular Maintenance

**Weekly:**
- Scan root directory for misplaced files
- Move any stray `.md`, `.sh`, `.json`, `.py` files to correct locations
- Update documentation indexes

**After Major Features:**
- Review new files created
- Ensure proper categorization
- Update subdirectory READMEs if needed

**Before Pull Requests:**
- Verify no organizational violations
- Check that new files follow conventions
- Confirm scripts have proper paths

## Anti-Patterns to Avoid

### ❌ Critical Violations

1. **Creating markdown docs in root**
   ```bash
   # WRONG
   touch NEW_FEATURE_SUMMARY.md

   # CORRECT
   touch docs/planning/NEW_FEATURE_SUMMARY.md
   ```

2. **Leaving scripts in root**
   ```bash
   # WRONG
   touch run_test.sh

   # CORRECT
   touch scripts/benchmarks/run_test.sh
   ```

3. **Debug files in root**
   ```bash
   # WRONG
   touch debug_output.json

   # CORRECT
   touch debug/debug_output.json
   ```

4. **Temporary files not cleaned up**
   ```bash
   # WRONG
   touch temp_test.py  # and forget about it

   # CORRECT
   touch tests/archive/temp_test_20251019.py  # with date
   # OR delete immediately after use
   ```

### ⚠️ Code Smells

- Multiple related markdown files appearing in root
- Scripts without category subdirectories
- Debug files scattered across repository
- Documentation without clear categorization
- Files named `temp*`, `test*`, `old*` outside archive/

## Recovery Protocol

If repository becomes disorganized:

1. **Audit:** Run `find . -maxdepth 1 -type f` to list root files
2. **Categorize:** Group files by type and purpose
3. **Create plan:** Document intended moves
4. **Execute:** Use `git mv` for all moves
5. **Update:** Fix paths, links, and references
6. **Verify:** Test all scripts and check links
7. **Document:** Update this file if patterns emerge
8. **Commit:** Single commit with full reorganization

## Benefits of This Structure

1. **Discoverability** - Clear hierarchy, files easy to find
2. **Maintainability** - Related files grouped together
3. **Scalability** - Structure handles growth without chaos
4. **Onboarding** - New contributors understand layout quickly
5. **Cleanliness** - Root directory stays uncluttered
6. **Professionalism** - Repository looks well-maintained

## Conclusion

**Follow these rules religiously.** A well-organized repository:
- Saves time (finding files is instant)
- Reduces cognitive load (clear mental model)
- Improves collaboration (everyone knows where things go)
- Prevents technical debt (no "cleanup needed" backlog)

**When in doubt:** File in the most specific subdirectory that fits. It's easier to move a file once than to search for it repeatedly.

---

**This is a living document.** Update it when new patterns emerge or structure needs refinement.
