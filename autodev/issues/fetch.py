"""Fetch issue details from GitHub."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from github import Github

logger = logging.getLogger(__name__)


def fetch_issue(repo: str, number: int) -> dict[str, Any]:
    """Fetch full issue details."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token not found")

    gh = Github(token)
    repo_obj = gh.get_repo(repo)
    issue = repo_obj.get_issue(number)

    return {
        "repo": repo,
        "repo_name": repo.split("/")[-1],
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "state": issue.state,
        "labels": [label.name for label in issue.labels],
        "url": issue.html_url,
        "created_at": issue.created_at.isoformat(),
        "comments": [
            {
                "author": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in issue.get_comments()
        ],
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=str, required=True)
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    issue = fetch_issue(args.repo, args.number)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(issue, f, indent=2)


if __name__ == "__main__":
    main()
