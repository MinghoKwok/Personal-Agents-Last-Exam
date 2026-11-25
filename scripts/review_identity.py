"""Review identities from GitHub metadata and trusted default-branch policy."""


def is_automated_reviewer(account):
    """GitHub uses different bot login spellings in requests, timelines and reviews."""
    account = account or {}
    login = (account.get("login") or "").casefold()
    return ((account.get("type", account.get("__typename", "")) or "").casefold() == "bot"
            or login.endswith("[bot]")
            or login in {"copilot", "copilot-pull-request-reviewer", "chatgpt-codex-connector"})


def can_self_review(login, user_id, rules):
    # Both values come from GitHub API identity fields, never PR text, labels,
    # commit author metadata or contributor-supplied policy files.
    return isinstance(user_id, int) and not isinstance(user_id, bool) and any(
        row.get("id") == user_id
        and row.get("login", "").casefold() == (login or "").casefold()
        for row in rules.get("self_review_maintainers", [])
    )
