# H13: FeatureFlagSchema - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 6 (Week 6)

---

## Overview

H13 (FeatureFlagSchema) defines configuration for gradual feature rollout and A/B testing, enabling safe deployment of new features with user-level overrides and percentage-based rollout.

## Goals

1. **User-Level Flags**: Enable/disable features for specific users
2. **Percentage Rollout**: Gradual rollout to X% of users
3. **Override Conditions**: Complex conditions for feature activation
4. **Fast Queries**: <10ms to check if feature enabled
5. **Environment Integration**: Works with existing config system

## Design

### Core Models

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Any

class RolloutStrategy(str, Enum):
    """Feature rollout strategy."""
    ALL = "all"  # Enabled for all users
    NONE = "none"  # Disabled for all users
    PERCENTAGE = "percentage"  # Percentage-based rollout
    USERS = "users"  # Specific user list
    CONDITIONAL = "conditional"  # Complex conditions

class FeatureFlag(BaseModel):
    """
    Configuration for a single feature flag.

    Example:
        >>> flag = FeatureFlag(
        ...     flag_name="new_error_recovery",
        ...     description="Enable H5 error recovery with retry",
        ...     strategy=RolloutStrategy.PERCENTAGE,
        ...     rollout_percentage=0.25,  # 25% rollout
        ...     enabled_for_users=["user-123"],
        ...     override_conditions={"env": "production"}
        ... )
    """
    flag_name: str = Field(..., pattern=r'^[a-z][a-z0-9_]*$', description="Feature flag identifier")
    description: str = Field("", description="Human-readable description")
    strategy: RolloutStrategy = Field(RolloutStrategy.NONE, description="Rollout strategy")

    # Percentage rollout
    rollout_percentage: float = Field(0.0, ge=0.0, le=1.0, description="Rollout percentage (0.0-1.0)")

    # User-level overrides
    enabled_for_users: list[str] = Field(default_factory=list, description="Always enabled for these users")
    disabled_for_users: list[str] = Field(default_factory=list, description="Always disabled for these users")

    # Conditional rollout
    override_conditions: dict[str, Any] = Field(default_factory=dict, description="Complex activation conditions")

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_by: str | None = None
    enabled: bool = Field(True, description="Master kill switch")

    @field_validator('rollout_percentage')
    def validate_percentage(cls, v, info):
        if info.data.get('strategy') == RolloutStrategy.PERCENTAGE and not (0.0 <= v <= 1.0):
            raise ValueError("rollout_percentage must be between 0.0 and 1.0")
        return v

class FeatureFlagConfig(BaseModel):
    """
    Collection of feature flags for the application.

    Provides fast lookup and evaluation of feature flags.
    """
    flags: dict[str, FeatureFlag] = Field(default_factory=dict, description="Flag name -> FeatureFlag")
    default_enabled: bool = Field(False, description="Default if flag not found")

    def get_flag(self, flag_name: str) -> FeatureFlag | None:
        """Get feature flag by name."""
        return self.flags.get(flag_name)

    def is_enabled(self, flag_name: str, user_id: str | None = None, context: dict | None = None) -> bool:
        """
        Check if feature is enabled for user/context.

        Evaluation order:
        1. Check if flag exists (return default_enabled if not)
        2. Check master kill switch (enabled field)
        3. Check disabled_for_users (explicit disable)
        4. Check enabled_for_users (explicit enable)
        5. Check strategy (ALL/NONE/PERCENTAGE/CONDITIONAL)

        Args:
            flag_name: Feature flag identifier
            user_id: User ID for user-level checks
            context: Additional context for conditional evaluation

        Returns:
            True if feature enabled, False otherwise
        """
        flag = self.get_flag(flag_name)
        if flag is None:
            return self.default_enabled

        # Master kill switch
        if not flag.enabled:
            return False

        # Explicit disable takes precedence
        if user_id and user_id in flag.disabled_for_users:
            return False

        # Explicit enable
        if user_id and user_id in flag.enabled_for_users:
            return True

        # Strategy-based evaluation
        if flag.strategy == RolloutStrategy.ALL:
            return True
        elif flag.strategy == RolloutStrategy.NONE:
            return False
        elif flag.strategy == RolloutStrategy.USERS:
            return user_id in flag.enabled_for_users if user_id else False
        elif flag.strategy == RolloutStrategy.PERCENTAGE:
            return self._evaluate_percentage(flag, user_id)
        elif flag.strategy == RolloutStrategy.CONDITIONAL:
            return self._evaluate_conditions(flag, context or {})

        return False

    def _evaluate_percentage(self, flag: FeatureFlag, user_id: str | None) -> bool:
        """Evaluate percentage rollout using consistent hashing."""
        if not user_id:
            return False

        # Consistent hash: same user always gets same result
        import hashlib
        hash_input = f"{flag.flag_name}:{user_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 100) / 100.0  # 0.00 to 0.99

        return bucket < flag.rollout_percentage

    def _evaluate_conditions(self, flag: FeatureFlag, context: dict) -> bool:
        """Evaluate conditional rollout."""
        # Simple key-value matching
        for key, expected_value in flag.override_conditions.items():
            if context.get(key) != expected_value:
                return False
        return True
```

## Acceptance Criteria

### AC1: Supports User-Level Overrides ✓

```python
def test_ac1_user_level_overrides():
    config = FeatureFlagConfig(flags={
        "test_feature": FeatureFlag(
            flag_name="test_feature",
            strategy=RolloutStrategy.NONE,
            enabled_for_users=["user-123", "user-456"]
        )
    })

    # Enabled for specific users
    assert config.is_enabled("test_feature", user_id="user-123") is True
    assert config.is_enabled("test_feature", user_id="user-456") is True

    # Disabled for others
    assert config.is_enabled("test_feature", user_id="user-999") is False
```

### AC2: Percentage Rollout Works Correctly ✓

```python
def test_ac2_percentage_rollout():
    config = FeatureFlagConfig(flags={
        "gradual_rollout": FeatureFlag(
            flag_name="gradual_rollout",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=0.5  # 50%
        )
    })

    # Test with 1000 users
    enabled_count = sum(
        config.is_enabled("gradual_rollout", user_id=f"user-{i}")
        for i in range(1000)
    )

    # Should be approximately 500 ± 50
    assert 450 <= enabled_count <= 550
```

### AC3: Query Time <10ms ✓

```python
def test_ac3_query_performance():
    config = FeatureFlagConfig(flags={
        f"flag_{i}": FeatureFlag(flag_name=f"flag_{i}", strategy=RolloutStrategy.ALL)
        for i in range(100)
    })

    import time
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        config.is_enabled("flag_50", user_id="user-123")
        end = time.perf_counter()
        times.append((end - start) * 1000)

    avg_time_ms = sum(times) / len(times)
    assert avg_time_ms < 10
```

### AC4: Integrates with Existing Config ✓

```python
def test_ac4_config_integration():
    # Load from environment/file
    config = FeatureFlagConfig.model_validate({
        "flags": {
            "new_feature": {
                "flag_name": "new_feature",
                "strategy": "percentage",
                "rollout_percentage": 0.25
            }
        },
        "default_enabled": False
    })

    assert config.is_enabled("new_feature", user_id="test") in [True, False]
    assert config.is_enabled("unknown_flag") is False
```

## Implementation Plan

1. Create `feature_flags.py` with models
2. Implement `FeatureFlag` with validation
3. Implement `FeatureFlagConfig` with evaluation logic
4. Create comprehensive tests (20+ tests)
5. Update `__init__.py` exports
6. Document usage patterns

## Usage Examples

### Basic Usage

```python
from lift_sys.dspy_signatures import FeatureFlagConfig, FeatureFlag, RolloutStrategy

# Initialize config
config = FeatureFlagConfig(flags={
    "error_recovery": FeatureFlag(
        flag_name="error_recovery",
        description="Enable H5 error recovery",
        strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=0.25
    ),
    "trace_viz": FeatureFlag(
        flag_name="trace_viz",
        description="Enable H7 trace visualization",
        strategy=RolloutStrategy.ALL
    )
})

# Check if enabled
if config.is_enabled("error_recovery", user_id="user-123"):
    # Use ErrorRecovery
    recovery = ErrorRecovery(...)
    result = await recovery.execute_with_retry(node, ctx, executor)
else:
    # Use without retry
    result = await executor.execute_single_with_isolation(node, ctx)
```

### Environment-Based Flags

```python
# In production
config = FeatureFlagConfig(flags={
    "beta_features": FeatureFlag(
        flag_name="beta_features",
        strategy=RolloutStrategy.CONDITIONAL,
        override_conditions={"env": "staging"}
    )
})

# Check with context
is_enabled = config.is_enabled("beta_features", context={"env": "staging"})  # True
is_enabled = config.is_enabled("beta_features", context={"env": "production"})  # False
```

## Future Enhancements

1. **Database Backend**: Store flags in Supabase for runtime updates
2. **Analytics**: Track flag evaluation metrics
3. **A/B Testing**: Variant support (A/B/C)
4. **Time-Based Rollout**: Enable at specific times
5. **Dependency Flags**: Flag depends on another flag

---

**Status**: Ready for implementation
**Next Steps**: Implement FeatureFlag models → Tests → Documentation
