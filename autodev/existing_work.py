"""Check for existing work in target repositories."""

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from github import Github

logger = logging.getLogger(__name__)


@dataclass
class ExistingWork:
    """Summary of existing work in a repository."""

    open_issues: list[dict[str, Any]]
    open_prs: list[dict[str, Any]]
    recent_commits: list[dict[str, Any]]
    in_progress_keywords: set[str]


def get_github_client() -> Github | None:
    """Get authenticated GitHub client."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return Github(token)
    return None


def check_existing_work(
    repo_name: str,
    repo_path: Path | None = None,
    days_back: int = 90,
) -> ExistingWork:
    """Check for existing work in a repository.

    Args:
        repo_name: Full repo name (owner/name)
        repo_path: Local path to repo for git history
        days_back: How many days back to check commits

    Returns:
        ExistingWork with issues, PRs, and commits
    """
    open_issues = []
    open_prs = []
    recent_commits = []
    in_progress_keywords: set[str] = set()

    gh = get_github_client()

    if gh:
        try:
            repo = gh.get_repo(repo_name)

            # Get open issues
            for issue in repo.get_issues(state="open"):
                if not issue.pull_request:  # Exclude PRs
                    issue_data = {
                        "number": issue.number,
                        "title": issue.title,
                        "labels": [l.name for l in issue.labels],
                        "created_at": issue.created_at.isoformat(),
                        "url": issue.html_url,
                    }
                    open_issues.append(issue_data)

                    # Extract keywords from issue titles
                    keywords = _extract_keywords(issue.title)
                    in_progress_keywords.update(keywords)

            # Get open PRs
            for pr in repo.get_pulls(state="open"):
                pr_data = {
                    "number": pr.number,
                    "title": pr.title,
                    "labels": [l.name for l in pr.labels],
                    "created_at": pr.created_at.isoformat(),
                    "url": pr.html_url,
                    "draft": pr.draft,
                }
                open_prs.append(pr_data)

                # Extract keywords from PR titles
                keywords = _extract_keywords(pr.title)
                in_progress_keywords.update(keywords)

            logger.info(
                f"Found {len(open_issues)} open issues and {len(open_prs)} open PRs in {repo_name}"
            )

        except Exception as e:
            logger.warning(f"Failed to fetch GitHub data for {repo_name}: {e}")

    # Get recent commits from local repo
    if repo_path and repo_path.exists():
        since_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        recent_commits = _get_recent_commits(repo_path, since_date)

        # Extract keywords from commit messages
        for commit in recent_commits:
            keywords = _extract_keywords(commit["message"])
            in_progress_keywords.update(keywords)

        logger.info(f"Found {len(recent_commits)} recent commits in {repo_name}")

    return ExistingWork(
        open_issues=open_issues,
        open_prs=open_prs,
        recent_commits=recent_commits,
        in_progress_keywords=in_progress_keywords,
    )


def _get_recent_commits(repo_path: Path, since: datetime) -> list[dict[str, Any]]:
    """Get recent commits from a git repository."""
    commits = []

    try:
        # Get commits since date
        since_str = since.strftime("%Y-%m-%d")
        result = subprocess.run(
            [
                "git", "log",
                f"--since={since_str}",
                "--pretty=format:%H|%s|%ai",
                "-100",  # Limit to 100 commits
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        commits.append({
                            "sha": parts[0][:8],
                            "message": parts[1],
                            "date": parts[2],
                        })

    except Exception as e:
        logger.warning(f"Failed to get commits: {e}")

    return commits


def _extract_keywords(text: str) -> set[str]:
    """Extract relevant keywords from text for matching."""
    text_lower = text.lower()
    keywords = set()

    # Protocol keywords
    protocols = [
        "openid4vci", "openid4vp", "oid4vci", "oid4vp",
        "siop", "siopv2", "siop-v2", "self-issued",
        "mdoc", "mdl", "18013", "iso18013",
        "oid4ida", "identity-assurance",
        "sd-jwt", "sdjwt", "selective-disclosure",
        "dcql", "presentation-exchange",
        "credential-offer", "credential_offer",
        "age-verification", "age_verification", "ageverification",
        "eudi", "eudiw", "arf",
    ]

    for protocol in protocols:
        if protocol in text_lower or protocol.replace("-", "") in text_lower.replace("-", ""):
            keywords.add(protocol.replace("-", "").replace("_", ""))

    return keywords


def format_existing_work_context(existing: ExistingWork) -> str:
    """Format existing work as context for the LLM."""
    lines = []

    if existing.open_issues:
        lines.append("## Open Issues (DO NOT duplicate these)")
        for issue in existing.open_issues[:20]:  # Limit to 20
            labels = ", ".join(issue["labels"][:3]) if issue["labels"] else "no labels"
            lines.append(f"- #{issue['number']}: {issue['title']} [{labels}]")
        lines.append("")

    if existing.open_prs:
        lines.append("## Open Pull Requests (work in progress)")
        for pr in existing.open_prs[:10]:
            draft = " [DRAFT]" if pr.get("draft") else ""
            lines.append(f"- #{pr['number']}: {pr['title']}{draft}")
        lines.append("")

    if existing.recent_commits:
        lines.append("## Recent Commits (last 90 days)")
        for commit in existing.recent_commits[:15]:
            lines.append(f"- {commit['sha']}: {commit['message']}")
        lines.append("")

    if existing.in_progress_keywords:
        lines.append(f"## Keywords indicating work in progress")
        lines.append(f"These topics appear to be actively worked on: {', '.join(sorted(existing.in_progress_keywords))}")
        lines.append("")

    return "\n".join(lines)


def is_duplicate_proposal(
    proposal_title: str,
    existing: ExistingWork,
    threshold: float = 0.6,
) -> tuple[bool, str | None]:
    """Check if a proposal duplicates existing work.

    Returns:
        Tuple of (is_duplicate, reason)
    """
    proposal_keywords = _extract_keywords(proposal_title)

    # Check against open issues
    for issue in existing.open_issues:
        issue_keywords = _extract_keywords(issue["title"])
        overlap = proposal_keywords & issue_keywords
        if overlap and len(overlap) / max(len(proposal_keywords), 1) >= threshold:
            return True, f"Similar to open issue #{issue['number']}: {issue['title']}"

    # Check against open PRs
    for pr in existing.open_prs:
        pr_keywords = _extract_keywords(pr["title"])
        overlap = proposal_keywords & pr_keywords
        if overlap and len(overlap) / max(len(proposal_keywords), 1) >= threshold:
            return True, f"Similar to open PR #{pr['number']}: {pr['title']}"

    # Check if keywords are in active work
    overlap_with_active = proposal_keywords & existing.in_progress_keywords
    if len(overlap_with_active) >= 2:  # Multiple keyword matches
        return True, f"Topics appear to be in active development: {', '.join(overlap_with_active)}"

    return False, None
