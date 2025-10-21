# Planning Scripts

Scripts for managing the meta-framework: design by typed holes.

## Available Scripts

### track_holes.py
Main hole tracking and management utility.

**Usage**:
```bash
# List all holes
python scripts/planning/track_holes.py list

# List ready holes
python scripts/planning/track_holes.py ready

# Show hole details
python scripts/planning/track_holes.py show H6

# Mark hole as resolved
python scripts/planning/track_holes.py resolve H6 --resolution lift_sys/dspy_signatures/node_interface.py

# Show phase status
python scripts/planning/track_holes.py phase-status 1

# Generate dependency graph
python scripts/planning/track_holes.py visualize --output docs/planning/dependency_graph.dot
```

### validate_resolution.py (TODO)
Test if a hole resolution satisfies all constraints.

### propagate_constraints.py (TODO)
Compute constraint propagation from a resolution.

### check_completeness.py (TODO)
Verify design completeness (all holes resolved, constraints satisfied).

## Workflow

1. **Start Phase N**: Check ready holes for phase
   ```bash
   python scripts/planning/track_holes.py ready --phase 1
   ```

2. **Work on Hole**: Implement resolution

3. **Validate**: (TODO) Test resolution
   ```bash
   python scripts/planning/validate_resolution.py H6 --prototype lift_sys/dspy_signatures/node_interface.py
   ```

4. **Resolve**: Mark as complete
   ```bash
   python scripts/planning/track_holes.py resolve H6 --resolution lift_sys/dspy_signatures/node_interface.py
   ```

5. **Propagate**: (TODO) Update dependent holes
   ```bash
   python scripts/planning/propagate_constraints.py H6 --resolution "BaseNode with async run() -> NextNode | End"
   ```

6. **Check Progress**:
   ```bash
   python scripts/planning/track_holes.py phase-status 1
   python scripts/planning/check_completeness.py  # TODO
   ```

## Documentation

- **Meta-Framework**: `docs/planning/META_FRAMEWORK_DESIGN_BY_HOLES.md`
- **Hole Inventory**: `docs/planning/HOLE_INVENTORY.md`
- **Constraint Log**: `docs/planning/CONSTRAINT_PROPAGATION_LOG.md`
- **Phase Gates**: `docs/planning/PHASE_GATES_VALIDATION.md`
