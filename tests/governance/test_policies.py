"""`policies.py` -- per-object-type approval flags and exceptions."""

from app.governance.governance_models import GovernedObjectType
from app.governance.policies import GovernancePolicy, is_approval_required


def test_default_policy_requires_approval_for_every_type() -> None:
    policy = GovernancePolicy()
    for object_type in GovernedObjectType:
        assert is_approval_required(policy, object_type, "any-id")


def test_disabling_flag_disables_requirement() -> None:
    policy = GovernancePolicy(dataset_approval_required=False)
    assert not is_approval_required(policy, GovernedObjectType.DATASET, "d-1")
    assert is_approval_required(policy, GovernedObjectType.STRATEGY, "s-1")


def test_exception_overrides_policy() -> None:
    policy = GovernancePolicy(exceptions={"d-1"})
    assert not is_approval_required(policy, GovernedObjectType.DATASET, "d-1")
    assert is_approval_required(policy, GovernedObjectType.DATASET, "d-2")


def test_policy_round_trip() -> None:
    policy = GovernancePolicy(strategy_approval_required=False, exceptions={"a", "b"})
    restored = GovernancePolicy.from_dict(policy.to_dict())
    assert restored.strategy_approval_required is False
    assert restored.exceptions == {"a", "b"}
