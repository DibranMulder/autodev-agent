"""Implement approved issues using Claude Code."""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from autodev.config import AutoDevConfig, get_repo_config

logger = logging.getLogger(__name__)


@dataclass
class ImplementationResult:
    """Result of an implementation attempt."""

    success: bool
    branch_name: str | None = None
    commit_sha: str | None = None
    commit_message: str | None = None
    pr_title: str | None = None
    pr_body: str | None = None
    error: str | None = None
    files_changed: list[str] | None = None


class Implementer:
    """Implement issues using Claude."""

    def __init__(self, config: AutoDevConfig):
        self.config = config
        self.client = Anthropic()

    def implement(
        self,
        repo: str,
        issue_number: int,
        repo_path: Path,
    ) -> ImplementationResult:
        """Implement an issue."""
        # Fetch issue details
        from autodev.issues.fetch import fetch_issue

        issue = fetch_issue(repo, issue_number)
        repo_name = repo.split("/")[-1]
        repo_config = get_repo_config(self.config, repo_name)

        if not repo_config:
            return ImplementationResult(
                success=False,
                error=f"No configuration found for repository {repo_name}",
            )

        # Gather repository context
        context = self._gather_context(repo_path, repo_config)

        # Generate implementation plan
        plan = self._generate_plan(issue, context, repo_config)

        if not plan.get("changes"):
            return ImplementationResult(
                success=False,
                error="No changes generated",
            )

        # Apply changes
        files_changed = []
        for change in plan["changes"]:
            try:
                self._apply_change(repo_path, change)
                files_changed.append(change["file"])
            except Exception as e:
                logger.error(f"Failed to apply change to {change['file']}: {e}")
                return ImplementationResult(
                    success=False,
                    error=f"Failed to apply changes: {e}",
                )

        # Get commit info
        commit_sha = self._get_current_sha(repo_path)

        return ImplementationResult(
            success=True,
            branch_name=f"autodev/issue-{issue_number}",
            commit_sha=commit_sha,
            commit_message=plan.get("commit_message", f"Implement #{issue_number}"),
            pr_title=plan.get("pr_title", issue["title"].replace("[AutoDev] ", "")),
            pr_body=self._format_pr_body(issue, plan),
            files_changed=files_changed,
        )

    def _gather_context(self, repo_path: Path, repo_config: Any) -> dict[str, Any]:
        """Gather context about the repository."""
        context: dict[str, Any] = {
            "files": {},
            "structure": [],
        }

        # Get relevant files based on focus areas
        extensions = {
            "Go": [".go"],
            "Dart": [".dart"],
            "YAML": [".yaml", ".yml"],
        }

        target_extensions = extensions.get(repo_config.language, [])

        for ext in target_extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                # Skip excluded paths
                rel_path = str(file_path.relative_to(repo_path))
                if any(excl in rel_path for excl in repo_config.excluded_paths):
                    continue

                # Read file content (limit size)
                try:
                    content = file_path.read_text()
                    if len(content) < 50000:  # Skip very large files
                        context["files"][rel_path] = content[:10000]
                except Exception:
                    pass

        context["structure"] = list(context["files"].keys())[:50]

        return context

    def _generate_plan(
        self,
        issue: dict[str, Any],
        context: dict[str, Any],
        repo_config: Any,
    ) -> dict[str, Any]:
        """Generate an implementation plan using Claude."""
        # Build prompt with issue and context
        files_sample = {}
        for file, content in list(context["files"].items())[:10]:
            files_sample[file] = content[:3000]

        prompt = f"""Implement this issue for the {repo_config.name} repository.

## Issue #{issue['number']}: {issue['title']}

{issue['body']}

## Repository Info
- Language: {repo_config.language}
- Focus areas: {', '.join(repo_config.focus_areas)}

## File Structure
{json.dumps(context['structure'], indent=2)}

## Sample Files
{json.dumps(files_sample, indent=2)}

## Instructions
Generate an implementation plan with specific file changes.
- Keep changes small and focused
- Follow existing code patterns
- Include tests for any new functionality
- Make sure changes are backwards compatible

Return JSON with this structure:
{{
    "changes": [
        {{
            "file": "path/to/file.go",
            "action": "modify|create|delete",
            "description": "What this change does",
            "content": "Full new content for the file (for create/modify)"
        }}
    ],
    "commit_message": "Descriptive commit message",
    "pr_title": "PR title",
    "pr_description": "What this PR does",
    "test_instructions": "How to test these changes"
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
            system="""You are an expert software developer implementing improvements for the Privacy by Design Foundation.
Generate clean, tested, maintainable code following existing patterns.
Return only valid JSON.""",
        )

        try:
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse implementation plan: {e}")
            return {"changes": [], "error": str(e)}

    def _apply_change(self, repo_path: Path, change: dict[str, Any]) -> None:
        """Apply a single change to the repository."""
        file_path = repo_path / change["file"]
        action = change.get("action", "modify")

        if action == "delete":
            if file_path.exists():
                file_path.unlink()
        elif action in ("create", "modify"):
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change["content"])
        else:
            raise ValueError(f"Unknown action: {action}")

    def _get_current_sha(self, repo_path: Path) -> str | None:
        """Get current commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def _format_pr_body(self, issue: dict[str, Any], plan: dict[str, Any]) -> str:
        """Format PR body."""
        return f"""## Summary

{plan.get('pr_description', 'Implementation of approved issue.')}

Closes #{issue['number']}

## Changes

{self._format_changes_list(plan.get('changes', []))}

## Testing

{plan.get('test_instructions', 'Run the test suite to verify changes.')}

---
*This PR was automatically generated by [AutoDev Agent](https://github.com/privacybydesign/autodev-agent).*
"""

    def _format_changes_list(self, changes: list[dict[str, Any]]) -> str:
        """Format list of changes."""
        if not changes:
            return "_No changes_"

        lines = []
        for change in changes:
            action = change.get("action", "modify")
            icon = {"create": "+", "modify": "~", "delete": "-"}.get(action, "?")
            lines.append(f"- [{icon}] `{change['file']}`: {change.get('description', 'Updated')}")

        return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from autodev.config import load_config

    config = load_config(args.config.parent)

    with open(args.issue) as f:
        issue = json.load(f)

    implementer = Implementer(config)
    result = implementer.implement(
        repo=issue["repo"],
        issue_number=issue["number"],
        repo_path=args.repo,
    )

    output = {
        "success": result.success,
        "branch_name": result.branch_name,
        "commit_sha": result.commit_sha,
        "commit_message": result.commit_message,
        "pr_title": result.pr_title,
        "pr_body": result.pr_body,
        "error": result.error,
        "files_changed": result.files_changed,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
