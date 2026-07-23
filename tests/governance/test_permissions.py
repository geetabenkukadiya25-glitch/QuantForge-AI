"""`permissions.py` -- capability matrix. No authentication is
implemented; this only checks the static `Role -> allowed actions` map."""

from app.governance.permissions import Role, can


def test_admin_can_do_everything_reviewer_cannot() -> None:
    assert can(Role.ADMIN, "publish")
    assert not can(Role.REVIEWER, "publish")


def test_reviewer_can_approve_researcher_cannot() -> None:
    assert can(Role.REVIEWER, "approve")
    assert not can(Role.RESEARCHER, "approve")


def test_researcher_can_submit() -> None:
    assert can(Role.RESEARCHER, "submit_for_review")


def test_read_only_can_do_nothing() -> None:
    assert not can(Role.READ_ONLY, "submit_for_review")
    assert not can(Role.READ_ONLY, "comment")


def test_unknown_action_denied() -> None:
    assert not can(Role.ADMIN, "delete_the_universe")
