"""Update tracking issue with activity."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from github import Github

logger = logging.getLogger(__name__)

TRACKING_ISSUE_TITLE = "[AutoDev] Activity Tracking"


def update_tracking_issue(
    tracking_repo: str,
    date: str,
    proposals: list[dict[str, Any]] | None = None,
    implementation_status: dict[str, Any] | None = None,
) -> None:
    """Update the tracking issue with today's activity."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token not found")

    gh = Github(token)
    repo = gh.get_repo(tracking_repo)

    # Find or create tracking issue
    tracking_issue = None
    for issue in repo.get_issues(state="open", labels=["autodev-tracking"]):
        if issue.title == TRACKING_ISSUE_TITLE:
            tracking_issue = issue
            break

    if not tracking_issue:
        # Create tracking issue
        tracking_issue = repo.create_issue(
            title=TRACKING_ISSUE_TITLE,
            body=_create_tracking_body(),
            labels=["autodev-tracking"],
        )
        logger.info(f"Created tracking issue #{tracking_issue.number}")

    # Add comment with today's activity
    comment_body = _format_activity_comment(date, proposals, implementation_status)
    tracking_issue.create_comment(comment_body)
    logger.info(f"Updated tracking issue with {date} activity")


def _create_tracking_body() -> str:
    """Create initial tracking issue body."""
    return """## AutoDev Agent Activity Tracking

This issue tracks all AutoDev Agent activity across Privacy by Design Foundation repositories.

### Monitored Repositories
- [irmago](https://github.com/privacybydesign/irmago)
- [irmamobile](https://github.com/privacybydesign/irmamobile)
- [pbdf-schememanager](https://github.com/privacybydesign/pbdf-schememanager)

### Workflow
1. **Discovery** (2 AM UTC): Agent analyzes repos and creates proposal issues
2. **Human Review**: Maintainers review and approve proposals by adding `autodev-approved` label
3. **Implementation** (4 AM UTC): Agent implements approved issues and creates draft PRs
4. **Human Review**: Maintainers review and merge draft PRs

### Daily Activity
See comments below for daily activity logs.

---
*Last updated automatically by AutoDev Agent*
"""


def _format_activity_comment(
    date: str,
    proposals: list[dict[str, Any]] | None = None,
    implementation_status: dict[str, Any] | None = None,
) -> str:
    """Format activity comment."""
    lines = [f"## Activity Report: {date}", ""]

    if proposals:
        lines.append("### New Proposals")
        for p in proposals:
            lines.append(f"- [{p['repo']}] {p['title']}")
        lines.append("")
    else:
        lines.append("### New Proposals")
        lines.append("_No new proposals today_")
        lines.append("")

    if implementation_status:
        lines.append("### Implementations")
        status = implementation_status.get("status", "unknown")
        issue = implementation_status.get("issue")
        pr_url = implementation_status.get("pr_url")

        if status == "pr_created":
            lines.append(f"- Issue #{issue}: PR created - {pr_url}")
        elif status == "tests_failed":
            lines.append(f"- Issue #{issue}: Implementation failed (tests)")
        else:
            lines.append(f"- Issue #{issue}: {status}")
        lines.append("")

    lines.append(f"---")
    lines.append(f"*Generated at {datetime.utcnow().isoformat()}Z*")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--proposals", type=Path)
    parser.add_argument("--date", type=str, required=True)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--repo", type=str)
    parser.add_argument("--status", type=str)
    parser.add_argument("--pr-url", type=str)
    parser.add_argument("--tracking-repo", type=str, default="privacybydesign/autodev-agent")
    args = parser.parse_args()

    proposals = None
    if args.proposals and args.proposals.exists():
        with open(args.proposals) as f:
            proposals = json.load(f)

    implementation_status = None
    if args.issue and args.status:
        implementation_status = {
            "issue": args.issue,
            "repo": args.repo,
            "status": args.status,
            "pr_url": args.pr_url,
        }

    update_tracking_issue(
        tracking_repo=args.tracking_repo,
        date=args.date,
        proposals=proposals,
        implementation_status=implementation_status,
    )


if __name__ == "__main__":
    main()
