"""
Tests for Feature Flags (H13).

Tests cover:
1. User-level overrides (AC1)
2. Percentage rollout distribution (AC2)
3. Query performance <10ms (AC3)
4. Config integration (AC4)
5. Model validation
6. Strategy evaluation
7. Consistent hashing
"""

from __future__ import annotations

import time

import pytest

from lift_sys.dspy_signatures.feature_flags import (
    FeatureFlag,
    FeatureFlagConfig,
    RolloutStrategy,
)

# =============================================================================
# AC1: User-Level Overrides
# =============================================================================


def test_ac1_enabled_for_users_overrides_none_strategy():
    """AC1: Users in enabled_for_users list get feature even when strategy=NONE."""
    config = FeatureFlagConfig(
        flags={
            "test_feature": FeatureFlag(
                flag_name="test_feature",
                strategy=RolloutStrategy.NONE,
                enabled_for_users=["user-123", "user-456"],
            )
        }
    )

    # Enabled for specific users
    assert config.is_enabled("test_feature", user_id="user-123") is True
    assert config.is_enabled("test_feature", user_id="user-456") is True

    # Disabled for others
    assert config.is_enabled("test_feature", user_id="user-999") is False


def test_ac1_disabled_for_users_overrides_all_strategy():
    """AC1: Users in disabled_for_users list don't get feature even when strategy=ALL."""
    config = FeatureFlagConfig(
        flags={
            "test_feature": FeatureFlag(
                flag_name="test_feature",
                strategy=RolloutStrategy.ALL,
                disabled_for_users=["user-banned"],
            )
        }
    )

    # Disabled for specific user
    assert config.is_enabled("test_feature", user_id="user-banned") is False

    # Enabled for others
    assert config.is_enabled("test_feature", user_id="user-123") is True
    assert config.is_enabled("test_feature", user_id="user-456") is True


def test_ac1_disabled_overrides_enabled():
    """AC1: disabled_for_users takes priority over enabled_for_users."""
    config = FeatureFlagConfig(
        flags={
            "test_feature": FeatureFlag(
                flag_name="test_feature",
                strategy=RolloutStrategy.NONE,
                enabled_for_users=["user-123"],
                disabled_for_users=["user-123"],  # Same user in both lists
            )
        }
    )

    # Disabled takes priority
    assert config.is_enabled("test_feature", user_id="user-123") is False


def test_ac1_override_works_with_percentage_strategy():
    """AC1: User-level overrides work with percentage rollout."""
    config = FeatureFlagConfig(
        flags={
            "gradual_rollout": FeatureFlag(
                flag_name="gradual_rollout",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.0,  # 0% rollout
                enabled_for_users=["vip-user"],
            )
        }
    )

    # VIP user gets feature despite 0% rollout
    assert config.is_enabled("gradual_rollout", user_id="vip-user") is True

    # Regular users don't get it
    assert config.is_enabled("gradual_rollout", user_id="user-123") is False


# =============================================================================
# AC2: Percentage Rollout
# =============================================================================


def test_ac2_percentage_rollout_distribution():
    """AC2: Percentage rollout achieves approximately correct distribution."""
    config = FeatureFlagConfig(
        flags={
            "gradual_rollout": FeatureFlag(
                flag_name="gradual_rollout",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.5,  # 50% rollout
            )
        }
    )

    # Test with 1000 users
    enabled_count = sum(
        config.is_enabled("gradual_rollout", user_id=f"user-{i}") for i in range(1000)
    )

    # Should be approximately 500 ± 50 (10% tolerance)
    assert 450 <= enabled_count <= 550, f"Expected ~500, got {enabled_count}"


def test_ac2_percentage_rollout_consistent_hashing():
    """AC2: Same user always gets same result (consistent hashing)."""
    config = FeatureFlagConfig(
        flags={
            "gradual_rollout": FeatureFlag(
                flag_name="gradual_rollout",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.5,
            )
        }
    )

    # Check same user 100 times
    user_id = "user-123"
    first_result = config.is_enabled("gradual_rollout", user_id=user_id)

    for _ in range(100):
        result = config.is_enabled("gradual_rollout", user_id=user_id)
        assert result == first_result, "User got different result on retry"


def test_ac2_percentage_rollout_edge_cases():
    """AC2: Percentage rollout handles 0% and 100% correctly."""
    config = FeatureFlagConfig(
        flags={
            "zero_percent": FeatureFlag(
                flag_name="zero_percent",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.0,
            ),
            "hundred_percent": FeatureFlag(
                flag_name="hundred_percent",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=1.0,
            ),
        }
    )

    # 0% rollout: nobody gets it
    for i in range(100):
        assert config.is_enabled("zero_percent", user_id=f"user-{i}") is False

    # 100% rollout: everyone gets it
    for i in range(100):
        assert config.is_enabled("hundred_percent", user_id=f"user-{i}") is True


def test_ac2_percentage_rollout_without_user_id():
    """AC2: Percentage rollout returns False when user_id is None."""
    config = FeatureFlagConfig(
        flags={
            "gradual_rollout": FeatureFlag(
                flag_name="gradual_rollout",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.5,
            )
        }
    )

    # No user_id provided
    assert config.is_enabled("gradual_rollout", user_id=None) is False
    assert config.is_enabled("gradual_rollout") is False


# =============================================================================
# AC3: Query Performance
# =============================================================================


def test_ac3_query_performance_under_10ms():
    """AC3: Feature flag queries complete in <10ms on average."""
    # Create config with 100 flags
    config = FeatureFlagConfig(
        flags={
            f"flag_{i}": FeatureFlag(flag_name=f"flag_{i}", strategy=RolloutStrategy.ALL)
            for i in range(100)
        }
    )

    # Benchmark 1000 queries
    times = []
    for _ in range(1000):
        start = time.perf_counter()
        config.is_enabled("flag_50", user_id="user-123")
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    avg_time_ms = sum(times) / len(times)
    assert avg_time_ms < 10, f"Average query time {avg_time_ms:.2f}ms exceeds 10ms"


def test_ac3_percentage_rollout_performance():
    """AC3: Percentage rollout with hashing still meets <10ms target."""
    config = FeatureFlagConfig(
        flags={
            "gradual_rollout": FeatureFlag(
                flag_name="gradual_rollout",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.5,
            )
        }
    )

    # Benchmark 1000 queries with percentage strategy
    times = []
    for i in range(1000):
        start = time.perf_counter()
        config.is_enabled("gradual_rollout", user_id=f"user-{i}")
        end = time.perf_counter()
        times.append((end - start) * 1000)

    avg_time_ms = sum(times) / len(times)
    assert avg_time_ms < 10, f"Percentage rollout avg time {avg_time_ms:.2f}ms exceeds 10ms"


# =============================================================================
# AC4: Config Integration
# =============================================================================


def test_ac4_load_from_dict():
    """AC4: FeatureFlagConfig can be loaded from dictionary."""
    config_dict = {
        "flags": {
            "new_feature": {
                "flag_name": "new_feature",
                "strategy": "percentage",
                "rollout_percentage": 0.25,
            }
        },
        "default_enabled": False,
    }

    config = FeatureFlagConfig.model_validate(config_dict)

    assert config.is_enabled("new_feature", user_id="test") in [True, False]
    assert config.is_enabled("unknown_flag") is False


def test_ac4_serialize_to_dict():
    """AC4: FeatureFlagConfig can be serialized to dictionary."""
    config = FeatureFlagConfig(
        flags={
            "test_feature": FeatureFlag(
                flag_name="test_feature",
                description="Test feature",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=0.5,
            )
        },
        default_enabled=False,
    )

    config_dict = config.model_dump()

    assert "flags" in config_dict
    assert "test_feature" in config_dict["flags"]
    assert config_dict["flags"]["test_feature"]["strategy"] == "percentage"
    assert config_dict["flags"]["test_feature"]["rollout_percentage"] == 0.5


def test_ac4_default_enabled_behavior():
    """AC4: default_enabled controls behavior for unknown flags."""
    config_with_default_on = FeatureFlagConfig(default_enabled=True)
    config_with_default_off = FeatureFlagConfig(default_enabled=False)

    # Unknown flag with default_enabled=True
    assert config_with_default_on.is_enabled("unknown_flag") is True

    # Unknown flag with default_enabled=False
    assert config_with_default_off.is_enabled("unknown_flag") is False


# =============================================================================
# Model Validation
# =============================================================================


def test_flag_name_validation_accepts_valid_names():
    """FeatureFlag accepts valid snake_case flag names."""
    valid_names = [
        "new_feature",
        "error_recovery",
        "beta_rollout",
        "test123",
        "feature_v2",
    ]

    for name in valid_names:
        flag = FeatureFlag(flag_name=name)
        assert flag.flag_name == name


def test_flag_name_validation_rejects_invalid_names():
    """FeatureFlag rejects invalid flag names (not snake_case)."""
    invalid_names = [
        "NewFeature",  # CamelCase
        "new-feature",  # kebab-case
        "new feature",  # spaces
        "123feature",  # starts with number
        "",  # empty
    ]

    for name in invalid_names:
        with pytest.raises(ValueError):
            FeatureFlag(flag_name=name)


def test_rollout_percentage_validation_accepts_valid_range():
    """FeatureFlag accepts rollout_percentage in [0.0, 1.0]."""
    valid_percentages = [0.0, 0.25, 0.5, 0.75, 1.0]

    for percentage in valid_percentages:
        flag = FeatureFlag(
            flag_name="test",
            strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=percentage,
        )
        assert flag.rollout_percentage == percentage


def test_rollout_percentage_validation_rejects_invalid_range():
    """FeatureFlag rejects rollout_percentage outside [0.0, 1.0]."""
    invalid_percentages = [-0.1, 1.1, 2.0, -1.0]

    for percentage in invalid_percentages:
        with pytest.raises(ValueError):
            FeatureFlag(
                flag_name="test",
                strategy=RolloutStrategy.PERCENTAGE,
                rollout_percentage=percentage,
            )


# =============================================================================
# Strategy Evaluation
# =============================================================================


def test_strategy_all_enables_for_everyone():
    """Strategy ALL enables feature for all users."""
    config = FeatureFlagConfig(
        flags={"all_users": FeatureFlag(flag_name="all_users", strategy=RolloutStrategy.ALL)}
    )

    # Enabled for all users
    for i in range(100):
        assert config.is_enabled("all_users", user_id=f"user-{i}") is True

    # Enabled without user_id
    assert config.is_enabled("all_users") is True


def test_strategy_none_disables_for_everyone():
    """Strategy NONE disables feature for all users."""
    config = FeatureFlagConfig(
        flags={"no_users": FeatureFlag(flag_name="no_users", strategy=RolloutStrategy.NONE)}
    )

    # Disabled for all users
    for i in range(100):
        assert config.is_enabled("no_users", user_id=f"user-{i}") is False

    # Disabled without user_id
    assert config.is_enabled("no_users") is False


def test_strategy_users_requires_user_in_list():
    """Strategy USERS enables only for users in enabled_for_users list."""
    config = FeatureFlagConfig(
        flags={
            "beta_users": FeatureFlag(
                flag_name="beta_users",
                strategy=RolloutStrategy.USERS,
                enabled_for_users=["user-123", "user-456"],
            )
        }
    )

    # Enabled for listed users
    assert config.is_enabled("beta_users", user_id="user-123") is True
    assert config.is_enabled("beta_users", user_id="user-456") is True

    # Disabled for unlisted users
    assert config.is_enabled("beta_users", user_id="user-999") is False

    # Disabled without user_id
    assert config.is_enabled("beta_users") is False


def test_strategy_conditional_matches_context():
    """Strategy CONDITIONAL enables when context matches conditions."""
    config = FeatureFlagConfig(
        flags={
            "staging_only": FeatureFlag(
                flag_name="staging_only",
                strategy=RolloutStrategy.CONDITIONAL,
                override_conditions={"env": "staging"},
            )
        }
    )

    # Enabled in staging
    assert config.is_enabled("staging_only", context={"env": "staging"}) is True

    # Disabled in production
    assert config.is_enabled("staging_only", context={"env": "production"}) is False

    # Disabled without context
    assert config.is_enabled("staging_only") is False


def test_strategy_conditional_requires_all_conditions():
    """Strategy CONDITIONAL requires ALL conditions to match."""
    config = FeatureFlagConfig(
        flags={
            "multi_condition": FeatureFlag(
                flag_name="multi_condition",
                strategy=RolloutStrategy.CONDITIONAL,
                override_conditions={"env": "staging", "region": "us-east"},
            )
        }
    )

    # All conditions match
    assert (
        config.is_enabled("multi_condition", context={"env": "staging", "region": "us-east"})
        is True
    )

    # Only one condition matches
    assert (
        config.is_enabled("multi_condition", context={"env": "staging", "region": "us-west"})
        is False
    )

    # No conditions match
    assert (
        config.is_enabled("multi_condition", context={"env": "production", "region": "us-west"})
        is False
    )


# =============================================================================
# Master Kill Switch
# =============================================================================


def test_master_kill_switch_disables_flag():
    """Master kill switch (enabled=False) disables flag entirely."""
    config = FeatureFlagConfig(
        flags={
            "disabled_feature": FeatureFlag(
                flag_name="disabled_feature",
                strategy=RolloutStrategy.ALL,
                enabled=False,  # Master kill switch
            )
        }
    )

    # Disabled despite strategy=ALL
    assert config.is_enabled("disabled_feature") is False
    assert config.is_enabled("disabled_feature", user_id="user-123") is False


def test_master_kill_switch_overrides_user_list():
    """Master kill switch overrides enabled_for_users list."""
    config = FeatureFlagConfig(
        flags={
            "disabled_feature": FeatureFlag(
                flag_name="disabled_feature",
                strategy=RolloutStrategy.NONE,
                enabled_for_users=["vip-user"],
                enabled=False,  # Master kill switch
            )
        }
    )

    # Disabled even for VIP user
    assert config.is_enabled("disabled_feature", user_id="vip-user") is False


# =============================================================================
# Config Management
# =============================================================================


def test_add_flag():
    """Add flag to config."""
    config = FeatureFlagConfig()

    flag = FeatureFlag(flag_name="new_feature", strategy=RolloutStrategy.ALL)
    config.add_flag(flag)

    assert config.is_enabled("new_feature") is True


def test_add_flag_overwrites_existing():
    """Adding flag with same name overwrites existing flag."""
    config = FeatureFlagConfig(
        flags={"test_feature": FeatureFlag(flag_name="test_feature", strategy=RolloutStrategy.NONE)}
    )

    # Initially disabled
    assert config.is_enabled("test_feature") is False

    # Overwrite with enabled flag
    config.add_flag(FeatureFlag(flag_name="test_feature", strategy=RolloutStrategy.ALL))

    # Now enabled
    assert config.is_enabled("test_feature") is True


def test_remove_flag():
    """Remove flag from config."""
    config = FeatureFlagConfig(
        flags={"test_feature": FeatureFlag(flag_name="test_feature", strategy=RolloutStrategy.ALL)}
    )

    # Initially present
    assert config.is_enabled("test_feature") is True

    # Remove flag
    result = config.remove_flag("test_feature")
    assert result is True

    # Now uses default_enabled
    assert config.is_enabled("test_feature") is False


def test_remove_flag_returns_false_if_not_found():
    """Removing non-existent flag returns False."""
    config = FeatureFlagConfig()

    result = config.remove_flag("nonexistent")
    assert result is False


def test_list_flags():
    """List all flags in config."""
    config = FeatureFlagConfig(
        flags={
            "flag1": FeatureFlag(flag_name="flag1", strategy=RolloutStrategy.ALL),
            "flag2": FeatureFlag(flag_name="flag2", strategy=RolloutStrategy.NONE, enabled=False),
        }
    )

    flags = config.list_flags()
    assert len(flags) == 2
    assert any(f.flag_name == "flag1" for f in flags)
    assert any(f.flag_name == "flag2" for f in flags)


def test_list_flags_enabled_only():
    """List only enabled flags."""
    config = FeatureFlagConfig(
        flags={
            "enabled_flag": FeatureFlag(
                flag_name="enabled_flag", strategy=RolloutStrategy.ALL, enabled=True
            ),
            "disabled_flag": FeatureFlag(
                flag_name="disabled_flag", strategy=RolloutStrategy.ALL, enabled=False
            ),
        }
    )

    enabled_flags = config.list_flags(enabled_only=True)
    assert len(enabled_flags) == 1
    assert enabled_flags[0].flag_name == "enabled_flag"


def test_get_flag():
    """Get flag by name."""
    config = FeatureFlagConfig(
        flags={"test_feature": FeatureFlag(flag_name="test_feature", strategy=RolloutStrategy.ALL)}
    )

    flag = config.get_flag("test_feature")
    assert flag is not None
    assert flag.flag_name == "test_feature"
    assert flag.strategy == RolloutStrategy.ALL


def test_get_flag_returns_none_if_not_found():
    """Getting non-existent flag returns None."""
    config = FeatureFlagConfig()

    flag = config.get_flag("nonexistent")
    assert flag is None


# =============================================================================
# Metadata
# =============================================================================


def test_flag_metadata_created_at():
    """FeatureFlag includes created_at timestamp."""
    flag = FeatureFlag(flag_name="test")

    assert flag.created_at is not None
    assert "T" in flag.created_at  # ISO format


def test_flag_metadata_created_by():
    """FeatureFlag supports created_by field."""
    flag = FeatureFlag(flag_name="test", created_by="admin-user")

    assert flag.created_by == "admin-user"


def test_flag_description():
    """FeatureFlag supports description field."""
    flag = FeatureFlag(flag_name="test", description="Test feature for beta users")

    assert flag.description == "Test feature for beta users"


# =============================================================================
# Edge Cases
# =============================================================================


def test_empty_config_uses_default_enabled():
    """Empty config uses default_enabled for all flags."""
    config = FeatureFlagConfig(default_enabled=True)

    assert config.is_enabled("any_flag") is True


def test_evaluation_with_none_user_id():
    """Evaluation with user_id=None works correctly."""
    config = FeatureFlagConfig(
        flags={
            "all_strategy": FeatureFlag(flag_name="all_strategy", strategy=RolloutStrategy.ALL),
            "users_strategy": FeatureFlag(
                flag_name="users_strategy",
                strategy=RolloutStrategy.USERS,
                enabled_for_users=["user-123"],
            ),
        }
    )

    # ALL strategy works without user_id
    assert config.is_enabled("all_strategy", user_id=None) is True

    # USERS strategy requires user_id
    assert config.is_enabled("users_strategy", user_id=None) is False


def test_evaluation_with_empty_context():
    """Evaluation with empty context works correctly."""
    config = FeatureFlagConfig(
        flags={
            "conditional": FeatureFlag(
                flag_name="conditional",
                strategy=RolloutStrategy.CONDITIONAL,
                override_conditions={"env": "staging"},
            )
        }
    )

    # Empty context doesn't match conditions
    assert config.is_enabled("conditional", context={}) is False


def test_flag_with_no_override_conditions():
    """CONDITIONAL strategy with no conditions always returns True."""
    config = FeatureFlagConfig(
        flags={
            "always_on": FeatureFlag(
                flag_name="always_on",
                strategy=RolloutStrategy.CONDITIONAL,
                override_conditions={},  # No conditions
            )
        }
    )

    # No conditions to fail, so returns True
    assert config.is_enabled("always_on", context={}) is True
    assert config.is_enabled("always_on", context={"env": "production"}) is True
