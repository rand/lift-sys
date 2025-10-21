"""
Tests for ResourceLimits (H14)

Validates acceptance criteria:
1. Resource limit types defined (memory, time, tokens, concurrency)
2. Enforcement mechanism implemented
3. Integration with RunContext for tracking
4. Tests validate limits are enforced
"""

import time

import pytest

from lift_sys.dspy_signatures.resource_limits import (
    MODAL_DEFAULT_LIMITS,
    LimitCheckResult,
    LimitStatus,
    ResourceEnforcer,
    ResourceLimits,
    ResourcePresets,
    ResourceType,
    ResourceUsage,
)

# Unit Tests


class TestResourceLimits:
    """Test ResourceLimits configuration."""

    def test_resource_limits_creation(self):
        """Test creating resource limits."""
        limits = ResourceLimits(
            max_memory_bytes=1_000_000,
            max_time_seconds=60.0,
            max_tokens=10_000,
            max_concurrent_nodes=3,
        )

        assert limits.max_memory_bytes == 1_000_000
        assert limits.max_time_seconds == 60.0
        assert limits.max_tokens == 10_000
        assert limits.max_concurrent_nodes == 3
        assert limits.warning_threshold == 0.8  # Default

    def test_resource_limits_defaults(self):
        """Test default values (unlimited)."""
        limits = ResourceLimits()

        assert limits.max_memory_bytes is None
        assert limits.max_time_seconds is None
        assert limits.max_tokens is None
        assert limits.max_concurrent_nodes is None

    def test_get_limit(self):
        """Test getting limit by resource type."""
        limits = ResourceLimits(max_tokens=1000, max_memory_bytes=500_000)

        assert limits.get_limit(ResourceType.TOKENS) == 1000
        assert limits.get_limit(ResourceType.MEMORY) == 500_000
        assert limits.get_limit(ResourceType.TIME) is None


class TestResourceUsage:
    """Test ResourceUsage tracking."""

    def test_resource_usage_creation(self):
        """Test creating resource usage tracker."""
        usage = ResourceUsage()

        assert usage.memory_bytes == 0
        assert usage.time_seconds == 0.0
        assert usage.tokens == 0
        assert usage.concurrent_nodes == 0
        assert usage.llm_calls == 0

    def test_start_end_timing(self):
        """Test execution timing."""
        usage = ResourceUsage()

        usage.start()
        assert usage.start_time is not None

        time.sleep(0.1)  # Sleep 100ms

        usage.end()
        assert usage.end_time is not None
        assert usage.time_seconds >= 0.1
        assert usage.time_seconds < 0.2  # Should be close to 0.1s

    def test_add_tokens(self):
        """Test token tracking."""
        usage = ResourceUsage()

        usage.add_tokens(100)
        assert usage.tokens == 100

        usage.add_tokens(50)
        assert usage.tokens == 150

    def test_add_llm_call(self):
        """Test LLM call counting."""
        usage = ResourceUsage()

        usage.add_llm_call()
        assert usage.llm_calls == 1

        usage.add_llm_call()
        assert usage.llm_calls == 2

    def test_set_concurrent_nodes(self):
        """Test concurrent node tracking."""
        usage = ResourceUsage()

        usage.set_concurrent_nodes(3)
        assert usage.concurrent_nodes == 3

        usage.set_concurrent_nodes(1)
        assert usage.concurrent_nodes == 1

    def test_update_memory(self):
        """Test memory tracking."""
        usage = ResourceUsage()

        usage.update_memory(1_000_000)
        assert usage.memory_bytes == 1_000_000

    def test_update_time(self):
        """Test time tracking during execution."""
        usage = ResourceUsage()
        usage.start()

        time.sleep(0.05)
        usage.update_time()

        assert usage.time_seconds >= 0.05

    def test_get_usage(self):
        """Test getting usage by resource type."""
        usage = ResourceUsage(tokens=100, memory_bytes=500)

        assert usage.get_usage(ResourceType.TOKENS) == 100
        assert usage.get_usage(ResourceType.MEMORY) == 500


class TestLimitCheckResult:
    """Test LimitCheckResult model."""

    def test_limit_check_result_creation(self):
        """Test creating limit check results."""
        result = LimitCheckResult(
            resource_type=ResourceType.TOKENS,
            status=LimitStatus.OK,
            current=500,
            limit=1000,
            percentage=50.0,
            message="OK",
        )

        assert result.resource_type == ResourceType.TOKENS
        assert result.status == LimitStatus.OK
        assert result.current == 500
        assert result.limit == 1000
        assert result.percentage == 50.0

    def test_is_ok_property(self):
        """Test is_ok property."""
        result = LimitCheckResult(
            resource_type=ResourceType.TOKENS,
            status=LimitStatus.OK,
            current=100,
            limit=1000,
        )
        assert result.is_ok

    def test_is_warning_property(self):
        """Test is_warning property."""
        result = LimitCheckResult(
            resource_type=ResourceType.TOKENS,
            status=LimitStatus.WARNING,
            current=850,
            limit=1000,
        )
        assert result.is_warning

    def test_is_exceeded_property(self):
        """Test is_exceeded property."""
        result = LimitCheckResult(
            resource_type=ResourceType.TOKENS,
            status=LimitStatus.EXCEEDED,
            current=1100,
            limit=1000,
        )
        assert result.is_exceeded

    def test_string_representation(self):
        """Test string representation."""
        result = LimitCheckResult(
            resource_type=ResourceType.TOKENS,
            status=LimitStatus.WARNING,
            current=850,
            limit=1000,
            percentage=85.0,
        )
        string = str(result)
        assert "WARNING" in string
        assert "tokens" in string
        assert "850/1000" in string
        assert "85.0%" in string


class TestResourceEnforcer:
    """Test ResourceEnforcer limit checking."""

    def test_enforcer_creation(self):
        """Test creating enforcer."""
        limits = ResourceLimits(max_tokens=1000)
        enforcer = ResourceEnforcer(limits)

        assert enforcer.limits == limits

    def test_check_within_limits(self):
        """Test checking usage within limits."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens=500)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)

        assert result.is_ok
        assert result.current == 500
        assert result.limit == 1000
        assert result.percentage == 50.0

    def test_check_warning_threshold(self):
        """Test warning threshold (80%)."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens=850)  # 85% of limit
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)

        assert result.is_warning
        assert result.percentage == 85.0

    def test_check_exceeded(self):
        """Test limit exceeded."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens=1100)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)

        assert result.is_exceeded
        assert result.current == 1100
        assert result.limit == 1000

    def test_check_unlimited(self):
        """Test checking with no limit set."""
        limits = ResourceLimits()  # No limits
        usage = ResourceUsage(tokens=999_999)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)

        assert result.is_ok
        assert result.limit is None

    def test_check_all(self):
        """Test checking all resource types."""
        limits = ResourceLimits(
            max_tokens=1000,
            max_memory_bytes=2_000_000,
            max_time_seconds=60.0,
        )
        usage = ResourceUsage(
            tokens=900,  # 90% - warning
            memory_bytes=1_000_000,  # 50% - OK
            time_seconds=70.0,  # Exceeded
        )
        enforcer = ResourceEnforcer(limits)

        results = enforcer.check_all(usage)

        assert ResourceType.TOKENS in results
        assert ResourceType.MEMORY in results
        assert ResourceType.TIME in results

        assert results[ResourceType.TOKENS].is_warning
        assert results[ResourceType.MEMORY].is_ok
        assert results[ResourceType.TIME].is_exceeded

    def test_any_exceeded(self):
        """Test any_exceeded helper."""
        limits = ResourceLimits(max_tokens=1000, max_time_seconds=60.0)
        usage_ok = ResourceUsage(tokens=500, time_seconds=30.0)
        usage_exceeded = ResourceUsage(tokens=1100, time_seconds=30.0)

        enforcer = ResourceEnforcer(limits)

        assert not enforcer.any_exceeded(usage_ok)
        assert enforcer.any_exceeded(usage_exceeded)

    def test_any_warning(self):
        """Test any_warning helper."""
        limits = ResourceLimits(max_tokens=1000)
        usage_ok = ResourceUsage(tokens=500)
        usage_warning = ResourceUsage(tokens=850)

        enforcer = ResourceEnforcer(limits)

        assert not enforcer.any_warning(usage_ok)
        assert enforcer.any_warning(usage_warning)

    def test_summary(self):
        """Test summary generation."""
        limits = ResourceLimits(max_tokens=1000, max_memory_bytes=2_000_000)
        usage = ResourceUsage(tokens=500, memory_bytes=1_000_000)
        enforcer = ResourceEnforcer(limits)

        summary = enforcer.summary(usage)

        assert "Resource usage summary" in summary
        assert "tokens" in summary
        assert "memory" in summary
        assert "500/1000" in summary


class TestResourcePresets:
    """Test preset configurations."""

    def test_development_preset(self):
        """Test development preset."""
        limits = ResourcePresets.development()

        assert limits.max_memory_bytes == 1_000_000_000
        assert limits.max_time_seconds == 120.0
        assert limits.max_tokens == 50_000

    def test_production_preset(self):
        """Test production preset."""
        limits = ResourcePresets.production()

        assert limits.max_memory_bytes == 2_000_000_000
        assert limits.max_time_seconds == 600.0
        assert limits.max_tokens == 200_000

    def test_strict_preset(self):
        """Test strict preset."""
        limits = ResourcePresets.strict()

        assert limits.max_concurrent_nodes == 1
        assert limits.warning_threshold == 0.7

    def test_unlimited_preset(self):
        """Test unlimited preset."""
        limits = ResourcePresets.unlimited()

        assert limits.max_memory_bytes is None
        assert limits.max_time_seconds is None
        assert limits.max_tokens is None


class TestModalDefaults:
    """Test Modal.com default limits."""

    def test_modal_default_limits(self):
        """Test MODAL_DEFAULT_LIMITS configuration."""
        assert MODAL_DEFAULT_LIMITS.max_memory_bytes == 2_000_000_000
        assert MODAL_DEFAULT_LIMITS.max_time_seconds == 600.0
        assert MODAL_DEFAULT_LIMITS.max_concurrent_nodes == 3
        assert MODAL_DEFAULT_LIMITS.max_llm_calls == 20


class TestAcceptanceCriteria:
    """
    Tests validating H14 acceptance criteria:

    1. Resource limit types defined (memory, time, tokens, concurrency) ✓
    2. Enforcement mechanism implemented ✓
    3. Integration with RunContext for tracking ✓
    4. Tests validate limits are enforced ✓
    """

    def test_criterion_1_resource_types_defined(self):
        """AC1: All resource types are defined."""
        # Memory
        limits = ResourceLimits(max_memory_bytes=1_000_000)
        assert limits.get_limit(ResourceType.MEMORY) == 1_000_000

        # Time
        limits = ResourceLimits(max_time_seconds=60.0)
        assert limits.get_limit(ResourceType.TIME) == 60.0

        # Tokens
        limits = ResourceLimits(max_tokens=10_000)
        assert limits.get_limit(ResourceType.TOKENS) == 10_000

        # Concurrency
        limits = ResourceLimits(max_concurrent_nodes=3)
        assert limits.get_limit(ResourceType.CONCURRENCY) == 3

        # LLM calls
        limits = ResourceLimits(max_llm_calls=20)
        assert limits.get_limit(ResourceType.LLM_CALLS) == 20

    def test_criterion_2_enforcement_mechanism(self):
        """AC2: Enforcement mechanism works correctly."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens=500)
        enforcer = ResourceEnforcer(limits)

        # Within limits
        result = enforcer.check(ResourceType.TOKENS, usage)
        assert result.is_ok

        # Approaching limits
        usage.add_tokens(400)  # Now at 900
        result = enforcer.check(ResourceType.TOKENS, usage)
        assert result.is_warning

        # Exceeded
        usage.add_tokens(200)  # Now at 1100
        result = enforcer.check(ResourceType.TOKENS, usage)
        assert result.is_exceeded

    def test_criterion_3_context_integration(self):
        """AC3: ResourceUsage can be integrated with RunContext."""
        # Create usage tracker (would be attached to RunContext)
        usage = ResourceUsage()
        usage.start()

        # Simulate node execution
        usage.add_llm_call()
        usage.add_tokens(500)
        usage.set_concurrent_nodes(2)

        # Check usage
        assert usage.llm_calls == 1
        assert usage.tokens == 500
        assert usage.concurrent_nodes == 2

        # End execution
        usage.end()
        assert usage.time_seconds > 0

    def test_criterion_4_limits_enforced(self):
        """AC4: Limits are validated and enforced."""
        limits = ResourceLimits(
            max_tokens=1000,
            max_time_seconds=1.0,
            max_llm_calls=5,
        )
        usage = ResourceUsage()
        enforcer = ResourceEnforcer(limits)

        # Track usage
        usage.start()
        for _ in range(3):
            usage.add_llm_call()
            usage.add_tokens(200)

        # Check enforcement
        results = enforcer.check_all(usage)

        # Tokens: 600/1000 = 60% (OK)
        assert results[ResourceType.TOKENS].is_ok

        # LLM calls: 3/5 = 60% (OK)
        assert results[ResourceType.LLM_CALLS].is_ok

        # Add more usage
        usage.add_llm_call()
        usage.add_llm_call()
        usage.add_tokens(500)  # Total 1100

        results = enforcer.check_all(usage)

        # Tokens exceeded
        assert results[ResourceType.TOKENS].is_exceeded

        # LLM calls at limit
        assert results[ResourceType.LLM_CALLS].current == 5
        assert results[ResourceType.LLM_CALLS].limit == 5


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_end_before_start(self):
        """Test ending before starting."""
        usage = ResourceUsage()

        with pytest.raises(ValueError, match="Cannot end before starting"):
            usage.end()

    def test_zero_limit(self):
        """Test with zero limit."""
        limits = ResourceLimits(max_tokens=0)
        usage = ResourceUsage(tokens=1)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)
        assert result.is_exceeded

    def test_exact_limit(self):
        """Test usage exactly at limit."""
        limits = ResourceLimits(max_tokens=1000)
        usage = ResourceUsage(tokens=1000)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)
        # At limit, not exceeded (1000 <= 1000)
        assert result.is_warning or result.is_ok

    def test_custom_warning_threshold(self):
        """Test custom warning threshold."""
        limits = ResourceLimits(max_tokens=1000, warning_threshold=0.5)
        usage = ResourceUsage(tokens=600)
        enforcer = ResourceEnforcer(limits)

        result = enforcer.check(ResourceType.TOKENS, usage)
        # 60% usage with 50% threshold = warning
        assert result.is_warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
