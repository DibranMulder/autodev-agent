"""Tracking issue management."""

import os
from typing import Any

from github import Github


def get_tracking_status(repo: str) -> dict[str, int]:
    """Get status counts for a repository."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"pending": 0, "approved": 0, "prs_open": 0, "merged": 0}

    gh = Github(token)

    try:
        repo_obj = gh.get_repo(repo)

        pending = len(list(repo_obj.get_issues(state="open", labels=["autodev-proposal"])))
        approved = len(list(repo_obj.get_issues(state="open", labels=["autodev-approved"])))
        prs_open = len(list(repo_obj.get_pulls(state="open")))
        # Can't easily count merged PRs with autodev label without more API calls

        return {
            "pending": pending,
            "approved": approved,
            "prs_open": prs_open,
            "merged": 0,  # Would need more complex query
        }
    except Exception:
        return {"pending": 0, "approved": 0, "prs_open": 0, "merged": 0}
