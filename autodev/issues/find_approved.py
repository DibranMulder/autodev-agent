"""Find approved issues ready for implementation."""

import json
import logging
import os
from typing import Any

from github import Github

logger = logging.getLogger(__name__)


def find_approved_issues(repos: list[str]) -> list[dict[str, Any]]:
    """Find all issues with autodev-approved label."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token not found")

    gh = Github(token)
    approved = []

    for repo_name in repos:
        try:
            repo = gh.get_repo(repo_name)
            issues = repo.get_issues(state="open", labels=["autodev-approved"])

            for issue in issues:
                # Skip if already has a linked PR
                if _has_linked_pr(issue):
                    logger.info(f"Skipping {repo_name}#{issue.number} - already has PR")
                    continue

                approved.append({
                    "repo": repo_name,
                    "repo_name": repo_name.split("/")[-1],
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "labels": [label.name for label in issue.labels],
                    "url": issue.html_url,
                })

        except Exception as e:
            logger.error(f"Error fetching issues from {repo_name}: {e}")

    return approved


def _has_linked_pr(issue) -> bool:
    """Check if issue has a linked PR (via comments or timeline)."""
    # Check comments for PR links
    for comment in issue.get_comments():
        if "Draft PR created:" in comment.body or "pull/" in comment.body:
            return True

    return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", type=str, required=True)
    parser.add_argument("--output-format", choices=["json", "github"], default="json")
    args = parser.parse_args()

    repos = args.repos.split(",")
    approved = find_approved_issues(repos)

    if args.output_format == "github":
        # Output for GitHub Actions
        if approved:
            print(f"issues={json.dumps(approved)}")
            print("has_issues=true")
        else:
            print("issues=[]")
            print("has_issues=false")
    else:
        print(json.dumps(approved, indent=2))


if __name__ == "__main__":
    main()
