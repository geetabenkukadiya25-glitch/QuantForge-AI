"""Sync policy settings section (Phase 17.9) -- mirrors
`app.settings_center`'s section-module shape (`defaults()`/`validate()`)."""

import dataclasses
from dataclasses import dataclass, field

from app.cloud_sync.sync_conflict import ConflictResolutionPolicy


@dataclass
class SyncPolicy:
    default_conflict_resolution: str = ConflictResolutionPolicy.MANUAL.value
    per_kind_overrides: dict[str, str] = field(default_factory=dict)
    auto_retry_enabled: bool = False
    max_retry_count: int = 3

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "SyncPolicy":
        return SyncPolicy(
            default_conflict_resolution=data.get("default_conflict_resolution", ConflictResolutionPolicy.MANUAL.value),
            per_kind_overrides=dict(data.get("per_kind_overrides", {})),
            auto_retry_enabled=data.get("auto_retry_enabled", False),
            max_retry_count=data.get("max_retry_count", 3),
        )


def defaults() -> SyncPolicy:
    return SyncPolicy(default_conflict_resolution=ConflictResolutionPolicy.MANUAL.value, per_kind_overrides={}, auto_retry_enabled=False, max_retry_count=3)


def validate(policy: SyncPolicy) -> list[str]:
    issues = []
    valid_values = {p.value for p in ConflictResolutionPolicy}
    if policy.default_conflict_resolution not in valid_values:
        issues.append(f"default_conflict_resolution must be one of {sorted(valid_values)}, got '{policy.default_conflict_resolution}'")
    for kind, value in policy.per_kind_overrides.items():
        if value not in valid_values:
            issues.append(f"per_kind_overrides['{kind}'] must be one of {sorted(valid_values)}, got '{value}'")
    if policy.max_retry_count < 0:
        issues.append("max_retry_count must be >= 0")
    return issues
