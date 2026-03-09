"""Analyze repositories for improvement opportunities."""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from autodev.config import AutoDevConfig, get_repo_config

logger = logging.getLogger(__name__)


class RepositoryAnalyzer:
    """Analyze repositories using Claude to find improvement opportunities."""

    def __init__(self, config: AutoDevConfig):
        self.config = config
        self.client = Anthropic()

    def analyze(
        self,
        repos_dir: Path,
        sources_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze all repositories for improvements."""
        results = {
            "analyzed_at": __import__("datetime").datetime.utcnow().isoformat(),
            "repositories": {},
        }

        for repo_config in self.config.repositories:
            repo_path = repos_dir / repo_config.name
            if not repo_path.exists():
                logger.warning(f"Repository {repo_config.name} not found at {repo_path}")
                continue

            logger.info(f"Analyzing {repo_config.name}...")
            analysis = self._analyze_repository(repo_path, repo_config, sources_data)
            results["repositories"][repo_config.name] = analysis

        return results

    def _analyze_repository(
        self,
        repo_path: Path,
        repo_config: Any,
        sources_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze a single repository."""
        # Gather repository context
        context = self._gather_context(repo_path, repo_config)

        # Build analysis prompt
        prompt = self._build_analysis_prompt(context, sources_data, repo_config)

        # Call Claude for analysis
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            system="""You are an expert software developer analyzing repositories for the Privacy by Design Foundation.
Your goal is to identify small, incremental improvements that:
1. Improve code quality, testing, or documentation
2. Align with EU digital identity standards (eIDAS, EUDI Wallet ARF)
3. Enhance security and privacy
4. Are testable and maintainable

Output your analysis as JSON with the structure:
{
    "summary": "Brief overview of the repository state",
    "opportunities": [
        {
            "category": "testing|security|standards|documentation|performance|refactoring",
            "title": "Short title for the improvement",
            "description": "Detailed description of what should be changed",
            "files_affected": ["list of files to modify"],
            "priority": 1-5 (1 highest),
            "effort": "small|medium|large",
            "rationale": "Why this improvement matters"
        }
    ]
}""",
        )

        # Parse response
        try:
            content = response.content[0].text
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return {
                "summary": "Analysis failed",
                "opportunities": [],
                "error": str(e),
            }

    def _gather_context(self, repo_path: Path, repo_config: Any) -> dict[str, Any]:
        """Gather context about a repository."""
        context: dict[str, Any] = {
            "structure": [],
            "readme": "",
            "recent_commits": [],
            "open_issues": [],
            "test_coverage": None,
        }

        # Get directory structure
        try:
            result = subprocess.run(
                ["find", ".", "-type", "f", "-name", "*.go", "-o", "-name", "*.dart",
                 "-o", "-name", "*.yaml", "-o", "-name", "*.json"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            files = [f for f in result.stdout.strip().split("\n") if f]
            # Filter out excluded paths
            for excluded in repo_config.excluded_paths:
                files = [f for f in files if excluded not in f]
            context["structure"] = files[:100]  # Limit
        except Exception as e:
            logger.warning(f"Failed to get structure: {e}")

        # Read README
        for readme_name in ["README.md", "README", "readme.md"]:
            readme_path = repo_path / readme_name
            if readme_path.exists():
                context["readme"] = readme_path.read_text()[:5000]
                break

        # Get recent commits
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-20"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            context["recent_commits"] = result.stdout.strip().split("\n")
        except Exception as e:
            logger.warning(f"Failed to get commits: {e}")

        return context

    def _build_analysis_prompt(
        self,
        context: dict[str, Any],
        sources_data: dict[str, Any],
        repo_config: Any,
    ) -> str:
        """Build the analysis prompt."""
        # Extract relevant source information
        source_summary = []
        for name, data in sources_data.get("sources", {}).items():
            if "error" not in data:
                content = data.get("content", {})
                headings = content.get("headings", [])
                source_summary.append(f"## {name}\nHeadings: {headings[:10]}")

        return f"""Analyze this repository for improvement opportunities.

## Repository: {repo_config.name}
Language: {repo_config.language}
Focus areas: {', '.join(repo_config.focus_areas)}

## File Structure (sample)
{chr(10).join(context['structure'][:50])}

## README
{context['readme'][:3000]}

## Recent Commits
{chr(10).join(context['recent_commits'])}

## Relevant Standards Updates
{chr(10).join(source_summary)}

## Task
Identify 3-5 small, incremental improvements for this repository. Focus on:
1. Test coverage gaps
2. Security improvements
3. Standards compliance (eIDAS 2.0, EUDI Wallet ARF)
4. Code quality
5. Documentation

Each improvement should be implementable in a single PR with clear acceptance criteria.
Return your analysis as JSON."""


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from autodev.config import load_config

    config = load_config(Path("config"))
    with open(args.sources) as f:
        sources_data = json.load(f)

    analyzer = RepositoryAnalyzer(config)
    results = analyzer.analyze(args.repos, sources_data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
