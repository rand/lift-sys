# Testing Protocol - MANDATORY

## Rule 1: NEVER run tests in background while making changes
- ❌ BAD: Start test → make changes → commit → wait for test
- ✅ GOOD: Make changes → commit → THEN start test

## Rule 2: Kill ALL background tests before making code changes
```bash
# Check running background jobs
jobs
# Kill specific job
kill %1
# Or use BashOutput to check status, then KillShell if running
```

## Rule 3: After code changes, verify NO stale tests are running
```bash
# Before running new test, check for old processes
ps aux | grep -E "(run_nontrivial|benchmark|diagnose)" | grep -v grep
```

## Rule 4: When committing fixes, follow this EXACT sequence:
1. Make code changes
2. Check for running background tests: `jobs`
3. Kill ALL background tests that might use the changed code
4. Commit the changes
5. Verify commit applied: `git log -1 --oneline`
6. ONLY THEN start validation test
7. Use a FRESH log file name with timestamp or "post-fix" suffix

## Rule 5: Use timestamped or descriptive log files
- ❌ BAD: `/tmp/phase2_test.log` (reused, confusing)
- ✅ GOOD: `/tmp/phase2_post_max_tokens_fix_$(date +%H%M%S).log`
- ✅ GOOD: `/tmp/phase2_verification_YYYYMMDD_HHMMSS.log`

## Rule 6: When user asks to "check on things", verify test used current code
Before reporting results:
1. Check when test started vs when code changed
2. Check log file timestamp vs commit timestamp
3. If test started BEFORE commit, DISCARD results and say:
   "That test ran with old code. Running fresh test with committed changes..."

## Rule 7: Document test runs in commit messages
```bash
# After running verification test
git commit -m "Verify fix works

Testing: Ran Phase 2 validation post-commit
Results: 9/10 passing (letter_grade now works)
Log: /tmp/phase2_YYYYMMDD_HHMMSS.log"
```

## Rule 8: Use bead-based workflow for complex testing
- Create bead for: make changes
- Create bead for: commit changes
- Create bead for: run tests
- Never overlap bead execution

## Violation Consequences
If I violate these rules:
1. STOP immediately when discovered
2. Acknowledge the waste of time to user
3. Kill stale tests
4. Start over with correct sequence
5. Update this protocol if new edge case found

## Quick Reference Card
```
CHANGE → COMMIT → VERIFY COMMITTED → KILL OLD TESTS → START NEW TEST
        ↓
    git log -1
        ↓
      jobs
        ↓
    kill %N (if needed)
        ↓
    FRESH test with timestamped log
```

## Auto-check before test runs
```bash
# Add this function to test scripts
verify_no_stale_tests() {
    if jobs | grep -q "run_nontrivial\|benchmark"; then
        echo "ERROR: Stale tests running. Kill them first!"
        exit 1
    fi
}
```
