"""Create GitHub issues from proposals."""

import logging
import os
from typing import Any

from github import Github

logger = logging.getLogger(__name__)


class IssueCreator:
    """Create GitHub issues from proposals."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token not found. Set GH_TOKEN or GITHUB_TOKEN.")
        self.gh = Github(self.token)

    def create_all(self, proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create issues for all proposals."""
        created = []

        for proposal in proposals:
            try:
                issue = self.create_issue(proposal)
                created.append(issue)
                logger.info(f"Created issue #{issue['number']} in {proposal['repo']}")
            except Exception as e:
                logger.error(f"Failed to create issue in {proposal['repo']}: {e}")

        return created

    def create_issue(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """Create a single GitHub issue."""
        repo = self.gh.get_repo(proposal["repo"])

        # Check for duplicate
        existing = repo.get_issues(state="open", labels=["autodev-proposal"])
        for issue in existing:
            if issue.title == proposal["title"]:
                logger.info(f"Issue already exists: {proposal['title']}")
                return {
                    "number": issue.number,
                    "url": issue.html_url,
                    "duplicate": True,
                }

        # Ensure labels exist
        existing_labels = {label.name for label in repo.get_labels()}
        for label in proposal.get("labels", []):
            if label not in existing_labels:
                try:
                    # Create label with appropriate color
                    color = self._get_label_color(label)
                    repo.create_label(name=label, color=color)
                except Exception:
                    pass  # Label might already exist

        # Create issue
        issue = repo.create_issue(
            title=proposal["title"],
            body=proposal["body"],
            labels=proposal.get("labels", []),
        )

        return {
            "number": issue.number,
            "url": issue.html_url,
            "repo": proposal["repo"],
            "title": proposal["title"],
            "duplicate": False,
        }

    def _get_label_color(self, label: str) -> str:
        """Get color for a label."""
        colors = {
            "autodev-proposal": "7057ff",  # Purple
            "autodev-approved": "0e8a16",  # Green
            "autodev-draft": "fbca04",     # Yellow
            "category:testing": "1d76db",
            "category:security": "d73a4a",
            "category:standards": "0075ca",
            "category:documentation": "0052cc",
            "category:performance": "5319e7",
            "category:refactoring": "006b75",
            "effort:small": "c2e0c6",
            "effort:medium": "fef2c0",
            "effort:large": "f9d0c4",
        }
        return colors.get(label, "ededed")


def main():
    """CLI entry point."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--repos", type=str, required=True)
    args = parser.parse_args()

    with open(args.proposals) as f:
        proposals = json.load(f)

    # Filter to specified repos
    allowed_repos = set(args.repos.split(","))
    proposals = [p for p in proposals if p["repo"] in allowed_repos]

    creator = IssueCreator()
    created = creator.create_all(proposals)

    print(f"Created {len(created)} issues")
    for issue in created:
        if not issue.get("duplicate"):
            print(f"  - {issue['repo']}#{issue['number']}: {issue.get('title', 'N/A')}")


if __name__ == "__main__":
    main()
