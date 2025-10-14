"""Improvement area detection for reverse-extracted IRs."""

from __future__ import annotations

from typing import Any

from ..ir.models import HoleKind, IntermediateRepresentation, TypedHole


class ImprovementDetector:
    """Detects improvement opportunities in reverse-extracted IRs."""

    def __init__(self):
        """Initialize the improvement detector."""
        pass

    def detect_improvements(
        self,
        ir: IntermediateRepresentation,
    ) -> list[TypedHole]:
        """
        Analyze IR and generate typed holes for improvement areas.

        Args:
            ir: Reverse-extracted intermediate representation

        Returns:
            List of typed holes prioritized by importance
        """
        all_holes = []

        # Phase 1: Security (highest priority)
        security_holes = self.detect_security_improvements(ir)
        all_holes.extend(security_holes)

        # Phase 2: Completeness (high priority)
        completeness_holes = self.detect_completeness_issues(ir)
        all_holes.extend(completeness_holes)

        # Phase 3: Error Handling (medium priority)
        error_holes = self.detect_error_handling_gaps(ir)
        all_holes.extend(error_holes)

        # Phase 4: Quality (medium priority)
        quality_holes = self.detect_quality_issues(ir)
        all_holes.extend(quality_holes)

        # Phase 5: Documentation (low priority)
        doc_holes = self.detect_documentation_gaps(ir)
        all_holes.extend(doc_holes)

        # Prioritize and deduplicate
        return self._prioritize_holes(all_holes)

    def detect_security_improvements(self, ir: IntermediateRepresentation) -> list[TypedHole]:
        """
        Identify security issues that should be addressed.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of typed holes for security improvements
        """
        holes = []

        # Extract CodeQL findings from evidence
        codeql_findings = [e for e in ir.metadata.evidence if e.get("analysis") == "codeql"]

        # Categorize by severity
        critical = [
            f for f in codeql_findings if f.get("metadata", {}).get("severity") == "critical"
        ]
        high = [f for f in codeql_findings if f.get("metadata", {}).get("severity") == "high"]
        medium = [f for f in codeql_findings if f.get("metadata", {}).get("severity") == "medium"]

        # Critical issues: Require immediate attention
        for finding in critical:
            holes.append(
                TypedHole(
                    identifier=f"security_critical_{finding['id']}",
                    type_hint="SecurityFix",
                    description=f"🔴 CRITICAL: {finding['message']}",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "severity": "critical",
                        "evidence_id": finding["id"],
                        "location": finding.get("location"),
                        "remediation": self._get_security_remediation(finding),
                    },
                )
            )

        # High-severity issues: Add as assertions
        for finding in high:
            holes.append(
                TypedHole(
                    identifier=f"security_high_{finding['id']}",
                    type_hint="SecurityAssertion",
                    description=f"🟠 HIGH: {finding['message']}",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "severity": "high",
                        "evidence_id": finding["id"],
                        "suggested_assertion": self._generate_security_assertion(finding),
                    },
                )
            )

        # Medium-severity: Optional improvements
        if medium:
            holes.append(
                TypedHole(
                    identifier="security_medium_batch",
                    type_hint="SecurityReview",
                    description=f"🟡 {len(medium)} medium-severity security issues found",
                    kind=HoleKind.INTENT,
                    constraints={
                        "severity": "medium",
                        "findings": medium,
                        "review_suggested": True,
                    },
                )
            )

        return holes

    def detect_completeness_issues(self, ir: IntermediateRepresentation) -> list[TypedHole]:
        """
        Identify missing or incomplete specifications.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of typed holes for completeness issues
        """
        holes = []

        # 1. Missing pre-conditions
        if len(ir.assertions) == 0:
            holes.append(
                TypedHole(
                    identifier="add_preconditions",
                    type_hint="AssertionList",
                    description="No pre-conditions specified. Consider adding input validation.",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "suggestions": [
                            "Validate input ranges (e.g., x > 0)",
                            "Check for null/None values",
                            "Verify data types match expectations",
                            "Ensure required fields are present",
                        ],
                    },
                )
            )

        # 2. Missing post-conditions
        has_postconditions = any(
            "return" in a.predicate.lower() or "result" in a.predicate.lower()
            for a in ir.assertions
        )
        if not has_postconditions and ir.signature.returns:
            holes.append(
                TypedHole(
                    identifier="add_postconditions",
                    type_hint="AssertionList",
                    description="No post-conditions specified. What guarantees does the return value provide?",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "suggestions": [
                            "Specify return value range or properties",
                            "Define success/failure conditions",
                            "Document invariants maintained",
                        ],
                    },
                )
            )

        # 3. Missing parameter types
        untyped_params = [
            p
            for p in ir.signature.parameters
            if not p.type_hint or p.type_hint == "Any" or p.type_hint == "unknown"
        ]
        for param in untyped_params:
            holes.append(
                TypedHole(
                    identifier=f"type_{param.name}",
                    type_hint="TypeAnnotation",
                    description=f"Parameter '{param.name}' has no type annotation",
                    kind=HoleKind.SIGNATURE,
                    constraints={
                        "parameter_name": param.name,
                        "inferred_usages": self._infer_type_from_usage(param, ir),
                    },
                )
            )

        # 4. Missing return type
        if not ir.signature.returns or ir.signature.returns == "unknown":
            holes.append(
                TypedHole(
                    identifier="return_type",
                    type_hint="TypeAnnotation",
                    description="Return type not specified",
                    kind=HoleKind.SIGNATURE,
                    constraints={
                        "inferred_from_code": self._infer_return_type(ir),
                    },
                )
            )

        # 5. Vague intent
        if len(ir.intent.summary.split()) < 5:
            holes.append(
                TypedHole(
                    identifier="clarify_intent",
                    type_hint="IntentDescription",
                    description="Intent description is too brief. Provide more detail.",
                    kind=HoleKind.INTENT,
                    constraints={
                        "current_length": len(ir.intent.summary.split()),
                        "suggestions": [
                            "What is the primary purpose?",
                            "What problem does this solve?",
                            "What are the key behaviors?",
                        ],
                    },
                )
            )

        # 6. Missing rationale
        if not ir.intent.rationale:
            holes.append(
                TypedHole(
                    identifier="add_rationale",
                    type_hint="IntentRationale",
                    description="No rationale provided. Why does this function exist?",
                    kind=HoleKind.INTENT,
                    constraints={
                        "suggestions": [
                            "Explain design decisions",
                            "Document why this approach was chosen",
                            "Note important constraints or trade-offs",
                        ],
                    },
                )
            )

        return holes

    def detect_error_handling_gaps(self, ir: IntermediateRepresentation) -> list[TypedHole]:
        """
        Identify missing error handling specifications.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of typed holes for error handling gaps
        """
        holes = []

        # 1. No exception specifications
        has_error_effects = any(
            "error" in e.description.lower() or "exception" in e.description.lower()
            for e in ir.effects
        )
        has_error_assertions = any(
            "error" in a.predicate.lower() or "exception" in a.predicate.lower()
            for a in ir.assertions
        )

        if not has_error_effects and not has_error_assertions:
            holes.append(
                TypedHole(
                    identifier="specify_error_handling",
                    type_hint="ErrorSpecification",
                    description="Error handling not specified. What exceptions can be raised?",
                    kind=HoleKind.EFFECT,
                    constraints={
                        "suggestions": [
                            "List possible exceptions",
                            "Specify error return values",
                            "Document error recovery behavior",
                            "Define failure modes",
                        ],
                    },
                )
            )

        # 2. Resource cleanup
        resource_effects = [
            e
            for e in ir.effects
            if any(kw in e.description.lower() for kw in ["open", "connect", "allocate", "acquire"])
        ]
        cleanup_effects = [
            e
            for e in ir.effects
            if any(kw in e.description.lower() for kw in ["close", "disconnect", "free", "release"])
        ]

        if resource_effects and not cleanup_effects:
            holes.append(
                TypedHole(
                    identifier="specify_resource_cleanup",
                    type_hint="ResourceManagement",
                    description="Resources acquired but cleanup not specified",
                    kind=HoleKind.EFFECT,
                    constraints={
                        "resources": [e.description for e in resource_effects],
                        "suggestions": [
                            "Add cleanup/close effects",
                            "Specify resource lifetime",
                            "Document cleanup guarantees",
                        ],
                    },
                )
            )

        return holes

    def detect_quality_issues(self, ir: IntermediateRepresentation) -> list[TypedHole]:
        """
        Identify specification quality issues.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of typed holes for quality issues
        """
        holes = []

        # Extract Daikon findings
        daikon_findings = [e for e in ir.metadata.evidence if e.get("analysis") == "daikon"]

        # 1. Weak invariants (always true)
        weak_invariants = [
            f for f in daikon_findings if "trivial" in f.get("metadata", {}).get("tags", [])
        ]
        if weak_invariants:
            holes.append(
                TypedHole(
                    identifier="strengthen_invariants",
                    type_hint="AssertionRefinement",
                    description=f"Found {len(weak_invariants)} trivial invariants. Consider strengthening.",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "weak_invariants": weak_invariants,
                        "suggestions": [
                            "Add more specific range constraints",
                            "Define relationships between variables",
                            "Specify ordering or uniqueness properties",
                        ],
                    },
                )
            )

        # 2. Conflicting invariants
        conflicts = self._detect_invariant_conflicts(ir.assertions, daikon_findings)
        for conflict in conflicts:
            holes.append(
                TypedHole(
                    identifier=f"resolve_conflict_{conflict['id']}",
                    type_hint="AssertionConflict",
                    description=f"Conflicting specifications: {conflict['description']}",
                    kind=HoleKind.ASSERTION,
                    constraints={
                        "conflict_detail": conflict,
                        "resolution_options": conflict.get("resolutions", []),
                    },
                )
            )

        # 3. Missing test coverage indicators
        if not self._has_test_evidence(ir):
            holes.append(
                TypedHole(
                    identifier="add_test_evidence",
                    type_hint="TestCoverage",
                    description="No test coverage evidence found. Dynamic analysis limited.",
                    kind=HoleKind.INTENT,
                    constraints={
                        "suggestions": [
                            "Add unit tests to enable Daikon analysis",
                            "Run dynamic invariant detection",
                            "Validate specifications against test cases",
                        ],
                    },
                )
            )

        return holes

    def detect_documentation_gaps(self, ir: IntermediateRepresentation) -> list[TypedHole]:
        """
        Identify documentation quality issues.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of typed holes for documentation gaps
        """
        holes = []

        # 1. Missing parameter descriptions
        undocumented_params = [
            p for p in ir.signature.parameters if not p.description or len(p.description) < 10
        ]
        if undocumented_params:
            holes.append(
                TypedHole(
                    identifier="document_parameters",
                    type_hint="Documentation",
                    description=f"{len(undocumented_params)} parameters lack detailed descriptions",
                    kind=HoleKind.SIGNATURE,
                    constraints={
                        "parameters": [p.name for p in undocumented_params],
                        "suggestions": [
                            "Explain parameter purpose and expected values",
                            "Document valid ranges or formats",
                            "Note relationships to other parameters",
                        ],
                    },
                )
            )

        # 2. Missing examples
        has_examples = any(
            keyword in ir.intent.summary.lower() for keyword in ["example", "e.g.", "for instance"]
        )
        if not has_examples:
            holes.append(
                TypedHole(
                    identifier="add_usage_examples",
                    type_hint="Documentation",
                    description="No usage examples provided",
                    kind=HoleKind.INTENT,
                    constraints={
                        "suggestions": [
                            "Add typical usage example",
                            "Show edge case handling",
                            "Demonstrate with concrete values",
                        ],
                    },
                )
            )

        return holes

    # Helper methods

    def _get_security_remediation(self, finding: dict[str, Any]) -> str:
        """Get remediation suggestion for a security finding."""
        message = finding.get("message", "").lower()

        # Common vulnerability patterns
        if "sql injection" in message:
            return "Add parameterized queries or use ORM"
        elif "path traversal" in message or "directory traversal" in message:
            return "Validate and sanitize file paths against whitelist"
        elif "xss" in message or "cross-site scripting" in message:
            return "Escape HTML output or use template engine"
        elif "hardcoded" in message and ("secret" in message or "password" in message):
            return "Move to environment variables or secret management"
        elif "command injection" in message:
            return "Use subprocess with argument list, avoid shell=True"
        elif "csrf" in message:
            return "Implement CSRF tokens for state-changing operations"
        elif "insecure random" in message:
            return "Use cryptographically secure random number generator"
        else:
            return "Review security advisory and apply recommended fixes"

    def _generate_security_assertion(self, finding: dict[str, Any]) -> str:
        """Generate a security assertion for a finding."""
        message = finding.get("message", "")

        if "sql injection" in message.lower():
            return "query parameters must be sanitized or parameterized"
        elif "path traversal" in message.lower():
            return "file paths must be validated against whitelist"
        elif "xss" in message.lower():
            return "user input must be escaped before rendering"
        elif "hardcoded" in message.lower():
            return "credentials must not be hardcoded"
        else:
            return f"security issue must be addressed: {message}"

    def _infer_type_from_usage(self, param: Any, ir: IntermediateRepresentation) -> list[str]:
        """Infer type hints from parameter usage in assertions/effects."""
        usages = []

        # Check assertions for clues
        param_name = getattr(param, "name", str(param))
        for assertion in ir.assertions:
            predicate = assertion.predicate.lower()
            if param_name in predicate:
                if ">" in predicate or "<" in predicate or "+" in predicate:
                    usages.append("numeric type (int or float)")
                if "len(" in predicate or "[" in predicate:
                    usages.append("sequence type (list, str, or tuple)")
                if ".get(" in predicate or "in" in predicate:
                    usages.append("dict or set")

        return usages if usages else ["unknown - no usage patterns detected"]

    def _infer_return_type(self, ir: IntermediateRepresentation) -> str:
        """Infer return type from assertions about the return value."""
        for assertion in ir.assertions:
            predicate = assertion.predicate.lower()
            if "return" in predicate or "result" in predicate:
                if ">" in predicate or "<" in predicate:
                    return "numeric (int or float)"
                if "len(" in predicate:
                    return "sequence (list, str, or tuple)"
                if "is none" in predicate or "none" in predicate:
                    return "Optional type"

        return "unknown - no return assertions found"

    def _detect_invariant_conflicts(
        self, assertions: list[Any], daikon_findings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect conflicting invariants between assertions and Daikon."""
        conflicts = []

        # Simple conflict detection: look for contradictory statements
        # This is a simplified implementation
        for i, assertion in enumerate(assertions):
            for finding in daikon_findings:
                finding_msg = finding.get("message", "").lower()
                assertion_text = assertion.predicate.lower()

                # Check for obvious contradictions
                if "always" in finding_msg and "never" in assertion_text:
                    conflicts.append(
                        {
                            "id": f"conflict_{i}",
                            "description": f"Assertion says '{assertion.predicate}' but Daikon found '{finding['message']}'",
                            "resolutions": [
                                "Update assertion to match observed behavior",
                                "Review Daikon evidence for accuracy",
                                "Code may have changed since analysis",
                            ],
                        }
                    )

        return conflicts

    def _has_test_evidence(self, ir: IntermediateRepresentation) -> bool:
        """Check if there is test coverage evidence."""
        # Look for Daikon findings (requires tests to run)
        daikon_findings = [e for e in ir.metadata.evidence if e.get("analysis") == "daikon"]

        # Look for test-related metadata
        has_test_metadata = any(
            "test" in e.get("metadata", {}).get("tags", []) for e in ir.metadata.evidence
        )

        return len(daikon_findings) > 0 or has_test_metadata

    def _prioritize_holes(self, holes: list[TypedHole]) -> list[TypedHole]:
        """
        Sort holes by priority.

        Args:
            holes: List of typed holes to prioritize

        Returns:
            Sorted list of holes
        """
        priority_order = {
            "security_critical": 0,
            "security_high": 1,
            "add_preconditions": 2,
            "add_postconditions": 3,
            "specify_error_handling": 4,
            "type_": 5,
            "security_medium": 6,
            "strengthen_invariants": 7,
            "clarify_intent": 8,
            "document_": 9,
            "add_usage_examples": 10,
            "add_rationale": 11,
            "add_test_evidence": 12,
            "specify_resource_cleanup": 13,
            "resolve_conflict": 14,
        }

        def get_priority(hole: TypedHole) -> int:
            for prefix, priority in priority_order.items():
                if hole.identifier.startswith(prefix):
                    return priority
            return 100  # Low priority for unmatched

        return sorted(holes, key=get_priority)


__all__ = ["ImprovementDetector"]
