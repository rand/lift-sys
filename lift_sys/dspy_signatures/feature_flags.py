"""
Feature Flags (H13)

Configuration for gradual feature rollout and A/B testing, enabling safe deployment
of new features with user-level overrides and percentage-based rollout.

This module provides:
1. FeatureFlag model with multiple rollout strategies
2. FeatureFlagConfig for managing multiple flags
3. Fast evaluation (<10ms) with consistent hashing
4. User-level overrides and conditional rollout

Design Principles:
1. Fast Evaluation: <10ms for flag checks
2. Consistent Hashing: Same user always gets same result for percentage rollout
3. Override Priority: disabled_for_users > enabled_for_users > strategy
4. Master Kill Switch: enabled field disables flag entirely
5. Default Behavior: Configurable default for unknown flags

Resolution for Hole H13: FeatureFlagSchema
Status: Implementation
Phase: 6 (Week 6)
Dependencies: None (independent configuration system)
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RolloutStrategy(str, Enum):
    """
    Feature rollout strategy.

    Strategies:
    - ALL: Enabled for all users
    - NONE: Disabled for all users
    - PERCENTAGE: Percentage-based rollout (0.0-1.0)
    - USERS: Enabled only for specific users
    - CONDITIONAL: Complex conditions (key-value matching)
    """

    ALL = "all"
    NONE = "none"
    PERCENTAGE = "percentage"
    USERS = "users"
    CONDITIONAL = "conditional"


class FeatureFlag(BaseModel):
    """
    Configuration for a single feature flag.

    Supports multiple rollout strategies with user-level overrides and
    conditional activation. Provides fast evaluation (<10ms) for production use.

    Example:
        >>> flag = FeatureFlag(
        ...     flag_name="new_error_recovery",
        ...     description="Enable H5 error recovery with retry",
        ...     strategy=RolloutStrategy.PERCENTAGE,
        ...     rollout_percentage=0.25,
        ...     enabled_for_users=["user-123"],
        ... )
        >>> # Check if enabled
        >>> is_enabled = flag_name in config.flags and config.is_enabled(flag_name, user_id)
    """

    flag_name: str = Field(
        ..., pattern=r"^[a-z][a-z0-9_]*$", description="Feature flag identifier (snake_case)"
    )
    description: str = Field("", description="Human-readable description of feature")
    strategy: RolloutStrategy = Field(
        RolloutStrategy.NONE, description="Rollout strategy for this flag"
    )

    # Percentage rollout
    rollout_percentage: float = Field(
        0.0, ge=0.0, le=1.0, description="Rollout percentage (0.0=0%, 1.0=100%)"
    )

    # User-level overrides
    enabled_for_users: list[str] = Field(
        default_factory=list, description="Always enabled for these user IDs"
    )
    disabled_for_users: list[str] = Field(
        default_factory=list, description="Always disabled for these user IDs"
    )

    # Conditional rollout
    override_conditions: dict[str, Any] = Field(
        default_factory=dict, description="Conditions for activation (key-value matching)"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="Flag creation time"
    )
    created_by: str | None = Field(None, description="User who created this flag")
    enabled: bool = Field(True, description="Master kill switch (disables flag entirely)")

    @field_validator("rollout_percentage")
    @classmethod
    def validate_percentage(cls, v: float, info) -> float:
        """Validate rollout_percentage is in valid range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"rollout_percentage must be between 0.0 and 1.0, got {v}")
        return v


class FeatureFlagConfig(BaseModel):
    """
    Collection of feature flags for the application.

    Provides fast lookup and evaluation of feature flags with support for
    user-level overrides, percentage rollout, and conditional activation.

    Evaluation order:
    1. Check if flag exists (return default_enabled if not)
    2. Check master kill switch (enabled field)
    3. Check disabled_for_users (explicit disable)
    4. Check enabled_for_users (explicit enable)
    5. Check strategy (ALL/NONE/PERCENTAGE/USERS/CONDITIONAL)

    Example:
        >>> config = FeatureFlagConfig(flags={
        ...     "error_recovery": FeatureFlag(
        ...         flag_name="error_recovery",
        ...         strategy=RolloutStrategy.PERCENTAGE,
        ...         rollout_percentage=0.5
        ...     )
        ... })
        >>> if config.is_enabled("error_recovery", user_id="user-123"):
        ...     # Use ErrorRecovery
        ...     recovery = ErrorRecovery(...)
    """

    flags: dict[str, FeatureFlag] = Field(
        default_factory=dict, description="Map of flag_name -> FeatureFlag"
    )
    default_enabled: bool = Field(False, description="Default value if flag not found")

    def get_flag(self, flag_name: str) -> FeatureFlag | None:
        """
        Get feature flag by name.

        Args:
            flag_name: Feature flag identifier

        Returns:
            FeatureFlag if exists, None otherwise
        """
        return self.flags.get(flag_name)

    def is_enabled(
        self, flag_name: str, user_id: str | None = None, context: dict | None = None
    ) -> bool:
        """
        Check if feature is enabled for user/context.

        Evaluation order (short-circuits on first match):
        1. Flag not found → return default_enabled
        2. Master kill switch (enabled=False) → return False
        3. User in disabled_for_users → return False
        4. User in enabled_for_users → return True
        5. Strategy evaluation → return result

        Args:
            flag_name: Feature flag identifier
            user_id: User ID for user-level checks (optional)
            context: Additional context for conditional evaluation (optional)

        Returns:
            True if feature enabled, False otherwise

        Example:
            >>> config.is_enabled("new_feature", user_id="user-123")
            True
            >>> config.is_enabled("beta_feature", context={"env": "staging"})
            False
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
        """
        Evaluate percentage rollout using consistent hashing.

        Uses SHA256 hash of flag_name:user_id to deterministically assign
        users to buckets (0-99). Same user always gets same result.

        Args:
            flag: FeatureFlag with rollout_percentage
            user_id: User ID for hashing

        Returns:
            True if user's bucket < rollout_percentage
        """
        if not user_id:
            return False

        # Consistent hash: same user + flag always gets same result
        hash_input = f"{flag.flag_name}:{user_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 100) / 100.0  # 0.00 to 0.99

        return bucket < flag.rollout_percentage

    def _evaluate_conditions(self, flag: FeatureFlag, context: dict) -> bool:
        """
        Evaluate conditional rollout with key-value matching.

        All conditions must match for flag to be enabled.

        Args:
            flag: FeatureFlag with override_conditions
            context: Context dictionary to match against

        Returns:
            True if all conditions match, False otherwise
        """
        # Simple key-value matching (all must match)
        for key, expected_value in flag.override_conditions.items():
            if context.get(key) != expected_value:
                return False
        return True

    def add_flag(self, flag: FeatureFlag) -> None:
        """
        Add or update a feature flag.

        Args:
            flag: FeatureFlag to add
        """
        self.flags[flag.flag_name] = flag

    def remove_flag(self, flag_name: str) -> bool:
        """
        Remove a feature flag.

        Args:
            flag_name: Flag identifier to remove

        Returns:
            True if flag was removed, False if not found
        """
        if flag_name in self.flags:
            del self.flags[flag_name]
            return True
        return False

    def list_flags(self, enabled_only: bool = False) -> list[FeatureFlag]:
        """
        List all feature flags.

        Args:
            enabled_only: If True, only return flags with enabled=True

        Returns:
            List of FeatureFlags
        """
        if enabled_only:
            return [f for f in self.flags.values() if f.enabled]
        return list(self.flags.values())


__all__ = [
    "RolloutStrategy",
    "FeatureFlag",
    "FeatureFlagConfig",
]
