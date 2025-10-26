# Whole-Project Reverse Mode Analysis Plan

> **Tracking**: This plan is tracked in Beads. Run `bd list` to see all issues or `bd ready` to see what's ready to work on.

## Overview
Make reverse mode analyze entire projects by default, with optional targeting of specific files.

**Goal**: Enable developers to quickly extract specifications from entire codebases, not just individual files, while maintaining backward compatibility with single-file analysis.

**Status**: Planning complete, 23 issues created with dependencies mapped

## Design Decision: Output Format

### Option 1: Multiple IRs (✅ Recommended)
- Return a list of IRs, one per analyzed file
- Schema: `IRResponse` becomes `{ irs: [IR], progress: [...] }`
- **Pros**: Clean separation, easy to understand which spec belongs to which file
- **Cons**: Requires API contract change

### Option 2: Aggregated IR
- Combine all findings into a single IR with multiple source files
- Schema: Keep current, but metadata.source_path becomes an array
- **Pros**: Minimal API changes
- **Cons**: Less clear structure, harder to navigate

**Decision: Use Option 1** - It's cleaner and more scalable.

---

## Implementation Tasks

### 1. Backend Schema Changes

**File**: `lift_sys/api/schemas.py`

```python
class ReverseRequest(BaseModel):
    module: str | None = None  # Make optional
    queries: list[str] = Field(default_factory=list)
    entrypoint: str = "main"
    analyses: list[str] = Field(
        default_factory=lambda: ["codeql", "daikon", "stack_graphs"]
    )
    stack_index_path: str | None = None

    # New field:
    analyze_all: bool = True  # Default to analyzing entire project

class IRResponse(BaseModel):
    irs: list[dict]  # Changed from single 'ir' to list 'irs'
    progress: list[dict] = Field(default_factory=list)

    @classmethod
    def from_irs(
        cls,
        irs: list[IntermediateRepresentation],
        *,
        progress: list[dict[str, object]] | None = None,
    ) -> IRResponse:
        return cls(irs=[ir.to_dict() for ir in irs], progress=progress or [])
```

### 2. Backend Lifter - File Discovery

**File**: `lift_sys/reverse_mode/lifter.py`

Add method to discover Python files:

```python
def discover_python_files(
    self,
    exclude_patterns: list[str] | None = None
) -> list[Path]:
    """Find all Python files in the repository.

    Args:
        exclude_patterns: Directory patterns to exclude

    Returns:
        List of Python file paths relative to repository root
    """
    if not self.repo:
        raise RuntimeError("Repository not loaded")

    repo_path = Path(self.repo.working_tree_dir)
    exclude = exclude_patterns or [
        "venv", ".venv", "node_modules", "__pycache__",
        ".git", "build", "dist", ".eggs", "*.egg-info"
    ]

    python_files = []
    for py_file in repo_path.rglob("*.py"):
        # Skip if in excluded directory
        if any(excl in py_file.parts for excl in exclude):
            continue
        # Skip if matches exclude pattern
        if any(py_file.match(excl) for excl in exclude if "*" in excl):
            continue
        python_files.append(py_file.relative_to(repo_path))

    return sorted(python_files)
```

### 3. Backend Lifter - Multi-File Lifting

**File**: `lift_sys/reverse_mode/lifter.py`

Add method for multi-file lifting:

```python
def lift_all(
    self,
    max_files: int | None = None
) -> list[IntermediateRepresentation]:
    """Lift specifications for all Python files in the repository.

    Args:
        max_files: Optional limit on number of files to analyze

    Returns:
        List of intermediate representations, one per file
    """
    files = self.discover_python_files()

    if max_files and len(files) > max_files:
        self._record_progress(f"limiting to first {max_files} of {len(files)} files")
        files = files[:max_files]

    irs = []
    failed = []

    for i, file_path in enumerate(files, 1):
        self._record_progress(f"analyzing:{file_path}:{i}/{len(files)}")
        try:
            ir = self.lift(str(file_path))
            irs.append(ir)
        except Exception as e:
            # Log error but continue with other files
            error_msg = f"error:{file_path}:{str(e)}"
            self._record_progress(error_msg)
            failed.append((file_path, str(e)))

    if failed:
        self._record_progress(f"completed with {len(failed)} failures")

    return irs
```

### 4. Backend API Endpoint Updates

**File**: `lift_sys/api/server.py`

Update the `/api/reverse` endpoint:

```python
@app.post("/api/reverse", response_model=IRResponse)
async def reverse(
    request: ReverseRequest,
    user: AuthenticatedUser = Depends(require_authenticated_user)
) -> IRResponse:
    LOGGER.info("%s initiated reverse lift", user.id)

    if not STATE.lifter:
        raise HTTPException(status_code=400, detail="lifter not configured")

    # Configure lifter
    analyses = set(request.analyses)
    stack_index = request.stack_index_path or getattr(
        STATE.lifter.config, "stack_index_path", None
    )
    STATE.lifter.config = LifterConfig(
        codeql_queries=request.queries or ["security/default"],
        daikon_entrypoint=request.entrypoint,
        stack_index_path=stack_index,
        run_codeql="codeql" in analyses,
        run_daikon="daikon" in analyses,
        run_stack_graphs="stack_graphs" in analyses,
    )

    # Choose analysis mode
    if request.module:
        # Single file mode
        await STATE.publish_progress({
            "type": "progress",
            "scope": "reverse",
            "stage": "initialise",
            "status": "running",
            "message": f"Analyzing single file: {request.module}",
        })
        ir = STATE.lifter.lift(request.module)
        irs = [ir]
    else:
        # Whole project mode (default)
        await STATE.publish_progress({
            "type": "progress",
            "scope": "reverse",
            "stage": "discovery",
            "status": "running",
            "message": "Discovering Python files in repository",
        })
        irs = STATE.lifter.lift_all()
        await STATE.publish_progress({
            "type": "progress",
            "scope": "reverse",
            "stage": "discovery",
            "status": "completed",
            "message": f"Analyzed {len(irs)} Python files",
        })

    # Load all IRs into planner
    for ir in irs:
        STATE.planner.load_ir(ir)

    await STATE.publish_progress({
        "type": "progress",
        "scope": "planner",
        "stage": "plan_ready",
        "status": "completed",
        "message": f"Planner loaded {len(irs)} IR(s)",
    })

    # Build progress summary
    now = datetime.now(UTC).isoformat() + "Z"
    progress = [
        {
            "id": "discovery",
            "label": "File Discovery",
            "status": "completed",
            "message": f"Found {len(irs)} Python files",
            "timestamp": now,
        },
        {
            "id": "analysis",
            "label": "Static Analysis",
            "status": "completed",
            "message": "CodeQL and Daikon analysis complete",
            "timestamp": now,
        },
        {
            "id": "planner_alignment",
            "label": "Planner Ready",
            "status": "completed",
            "message": "Specifications loaded into planner",
            "timestamp": now,
            "actions": [
                {"label": "View Results", "value": "open_results"},
            ],
        },
    ]

    return IRResponse.from_irs(irs, progress=progress)
```

### 5. Frontend UI - Mode Toggle

**File**: `frontend/src/views/RepositoryView.tsx`

Add state for analysis mode:

```typescript
const [analyzeMode, setAnalyzeMode] = useState<"project" | "file">("project");
```

Update the UI:

```tsx
<div className="space-y-4">
  <div>
    <h3 className="text-lg font-semibold mb-2">Reverse Mode Analysis</h3>
    <p className="text-sm text-muted-foreground">
      Extract specifications from existing code using static and dynamic analysis.
    </p>
  </div>

  {/* Mode Toggle */}
  <div className="space-y-2">
    <Label>Analysis Scope</Label>
    <div className="flex gap-2">
      <Button
        variant={analyzeMode === "project" ? "default" : "outline"}
        size="sm"
        onClick={() => setAnalyzeMode("project")}
        disabled={!activeRepository}
      >
        <FileCode className="h-4 w-4 mr-2" />
        Entire Project
      </Button>
      <Button
        variant={analyzeMode === "file" ? "default" : "outline"}
        size="sm"
        onClick={() => setAnalyzeMode("file")}
        disabled={!activeRepository}
      >
        <File className="h-4 w-4 mr-2" />
        Specific File
      </Button>
    </div>
  </div>

  {/* Conditional inputs based on mode */}
  {analyzeMode === "project" ? (
    <Alert>
      <AlertDescription>
        Will analyze all Python files in the repository, excluding common
        directories like venv, node_modules, and __pycache__.
      </AlertDescription>
    </Alert>
  ) : (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="space-y-2">
        <Label htmlFor="module">Target Module Path</Label>
        <Input
          id="module"
          value={moduleName}
          onChange={(e) => setModuleName(e.target.value)}
          placeholder="src/main.py"
          disabled={!activeRepository}
        />
        <p className="text-xs text-muted-foreground">
          Path relative to repository root
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="entrypoint">Entrypoint Function</Label>
        <Input
          id="entrypoint"
          value={entrypoint}
          onChange={(e) => setEntrypoint(e.target.value)}
          placeholder="main"
          disabled={!activeRepository}
        />
        <p className="text-xs text-muted-foreground">
          Function to analyze for invariants
        </p>
      </div>
    </div>
  )}
</div>
```

### 6. Frontend UI - Results Display

**File**: `frontend/src/views/RepositoryView.tsx`

Update mutation to handle new response format:

```typescript
const reverseMutation = useMutation({
  mutationFn: async () => {
    const response = await api.post("/api/reverse", {
      module: analyzeMode === "file" ? moduleName : null,
      queries: ["security/default"],
      entrypoint,
      analyze_all: analyzeMode === "project",
    });
    processedEvents.current = new Set();
    setTimeline(response.data.progress ?? []);
    return response.data;
  },
  onSuccess: (data) => {
    // Store the IRs for display
    if (data.irs && data.irs.length > 0) {
      console.log(`Received ${data.irs.length} IR(s)`);
      // TODO: Navigate to results view or display inline
    }
  },
});
```

Add results summary section:

```tsx
{reverseMutation.isSuccess && reverseMutation.data?.irs && (
  <Card>
    <CardHeader>
      <CardTitle>Analysis Results</CardTitle>
      <CardDescription>
        Specifications extracted from {reverseMutation.data.irs.length} file(s)
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div className="space-y-2">
        {reverseMutation.data.irs.map((ir: any, idx: number) => (
          <Card key={idx} className="p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-semibold">
                  {ir.metadata?.source_path || `File ${idx + 1}`}
                </div>
                <div className="text-sm text-muted-foreground">
                  {ir.intent?.summary}
                </div>
              </div>
              <Button variant="outline" size="sm">
                View Details
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </CardContent>
  </Card>
)}
```

---

## Migration Strategy

### Phase 1: Backend Foundation (1-2 days)
- [ ] Update schemas (ReverseRequest, IRResponse)
- [ ] Add file discovery to SpecificationLifter
- [ ] Add multi-file lifting capability
- [ ] Update /api/reverse endpoint

### Phase 2: Frontend UI (1 day)
- [ ] Add mode toggle (project vs file)
- [ ] Make module input conditional
- [ ] Update mutation to pass correct parameters

### Phase 3: Results Display (1-2 days)
- [ ] Create multi-IR results view
- [ ] Add filtering/search through files
- [ ] Add navigation between file specs
- [ ] Show summary statistics

### Phase 4: Polish & Optimization (1 day)
- [ ] Add progress indicators for multi-file
- [ ] Implement parallel analysis
- [ ] Add error recovery
- [ ] Performance testing with large repos

---

## Testing Plan

### Unit Tests
- [ ] `test_discover_python_files()` - File discovery logic
- [ ] `test_lift_all()` - Multi-file lifting
- [ ] `test_lift_all_with_errors()` - Error handling

### Integration Tests
- [ ] Test with small repo (5-10 files)
- [ ] Test with medium repo (50-100 files)
- [ ] Test with single file mode (backward compatibility)
- [ ] Test with excluded directories

### E2E Tests
- [ ] Complete flow: select repo → open → analyze all
- [ ] Complete flow: select repo → open → analyze single file
- [ ] Verify results display for multi-file

### Performance Tests
- [ ] Large repo (1000+ files) - should handle gracefully
- [ ] Memory usage profiling
- [ ] Parallel vs sequential analysis comparison

---

## Implementation Decisions

### 1. Performance Limits
**Decision**: Add configurable `max_files` limit (default: 100) with UI warning
- **Rationale**: Prevents timeouts and resource exhaustion on large repos
- **Implementation**: lift-sys-21 (P2)
- **Override**: Allow users to increase limit with explicit confirmation

### 2. Progress Feedback
**Decision**: Implement real-time progress with WebSocket events
- **Format**: `"Analyzing: {filename} ({current}/{total})"`
- **Implementation**: lift-sys-17 (P1)
- **UX**: Show cancellable progress dialog with file-by-file updates

### 3. Results Navigation
**Decision**: Start with flat list + search, consider tree view for v2
- **Phase 1**: Card-based list with search/filter (lift-sys-12, lift-sys-13)
- **Phase 2**: Add tree view grouped by directory structure
- **Rationale**: Simpler implementation, can iterate based on user feedback

### 4. Caching Strategy
**Decision**: Defer to Phase 2 (post-MVP)
- **Future**: Cache IRs with file hash keys in SQLite
- **Invalidation**: Check file modification time + content hash
- **Benefit**: Avoid re-analyzing unchanged files on repeated runs

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API contract breaking change affects existing clients | High | Medium | Careful versioning, deprecation warnings, maintain backward compat |
| Large repos cause timeout/memory issues | High | High | Implement max_files limit, add streaming results, optimize memory |
| File discovery misses important files | Medium | Low | Comprehensive exclusion testing, allow custom patterns |
| Analysis failures hard to debug | Medium | Medium | Detailed error messages with context, logging to observability |
| Poor performance with 100+ files | Medium | High | Implement parallel analysis, progress cancellation, lazy loading |

### UX Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Mode toggle confuses users | Medium | Medium | Clear labels, helpful tooltips, default to project mode |
| Results overwhelming with many files | High | High | Implement search/filter early, add summary statistics |
| Users don't understand progress | Low | Medium | Real-time file-by-file progress, estimated time remaining |

### Mitigation Actions

1. **Incremental Rollout**: Deploy behind feature flag initially
2. **Performance Monitoring**: Add metrics for analysis time, memory usage, success rate
3. **User Testing**: Test with 3-5 users before GA release
4. **Rollback Plan**: Keep old single-file endpoint available temporarily
5. **Documentation**: Comprehensive guide with examples and troubleshooting

---

## Success Criteria

### Functional Requirements
- ✅ Default behavior analyzes entire project (not just one file)
- ✅ Single file mode still works (backward compatible with existing workflows)
- ✅ Clear UI toggle between "Entire Project" and "Specific File" modes
- ✅ Results clearly show which spec belongs to which file (source path visible)
- ✅ Can handle repos with 100+ Python files without timeout
- ✅ Real-time progress feedback showing "Analyzing file X of Y"
- ✅ Graceful error handling when individual files fail (partial results returned)

### Quality Requirements
- ✅ All existing backend tests pass (0 regressions)
- ✅ All existing frontend tests pass (0 regressions)
- ✅ New unit tests for file discovery and lift_all() achieve >80% coverage
- ✅ Integration tests for both single-file and multi-file modes pass
- ✅ E2E tests demonstrate complete user flows for both modes
- ✅ Performance: <5s for small repos (<10 files), <30s for medium repos (<50 files)

### Documentation Requirements
- ✅ API documentation updated with new schema and examples
- ✅ User guide includes both analysis modes with screenshots
- ✅ Configuration options documented (max_files, exclusions)
- ✅ Migration guide for API consumers (if breaking changes required)

---

## Working with Beads

This plan is tracked using Beads, our dependency-aware issue tracker. Here's how to work with it:

### View All Issues
```bash
bd list                    # List all issues
bd list --priority 0       # Show only P0 issues
bd list --status open      # Show only open issues
```

### See What's Ready to Work On
```bash
bd ready                   # Shows unblocked issues ready to start
```

This is the most important command! It shows only issues that have no blocking dependencies.

### Start Working on an Issue
```bash
bd update lift-sys-2 --status in_progress --assignee "your-name"
```

### View Dependencies
```bash
bd dep tree lift-sys-5     # See dependency tree for API endpoint task
bd dep tree lift-sys-10    # See what blocks the frontend mutation
```

### Complete an Issue
```bash
bd close lift-sys-2 --reason "Implemented and tested"
```

### Current State (as of plan creation)

- **Total Issues**: 23
- **P0 (Highest)**: 9 issues - Core functionality
- **P1 (High)**: 9 issues - Important features and testing
- **P2 (Medium)**: 5 issues - Polish and optimization

**Ready to Start**: 10 issues have no blockers currently:
- `lift-sys-2`: Update API schemas (P0)
- `lift-sys-3`: Implement file discovery (P0)
- `lift-sys-8`: Add mode toggle component (P0)
- And 7 more...

### Recommended Start Order

1. **Backend First**: Start with `lift-sys-2` (schemas) and `lift-sys-3` (file discovery)
2. **Then Core**: Build `lift-sys-4` (lift_all) and `lift-sys-5` (API endpoint)
3. **Parallel Frontend**: While backend stabilizes, work on `lift-sys-8` and `lift-sys-9` (UI)
4. **Integration**: Connect frontend and backend with `lift-sys-10`
5. **Testing**: Once implementation stable, tackle `lift-sys-6`, `lift-sys-18`, `lift-sys-19`
6. **Polish**: Finally work on P2 items like progress indicators and documentation

Run `bd ready` frequently to see what's unblocked as you make progress!
