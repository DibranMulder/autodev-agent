#!/usr/bin/env python3
"""Main entry point for AutoDev Agent."""

import json
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from autodev.sources.fetch import SourceFetcher
from autodev.analyze import RepositoryAnalyzer
from autodev.propose import ProposalGenerator
from autodev.issues.create import IssueCreator
from autodev.implement import Implementer
from autodev.config import load_config

app = typer.Typer(
    name="autodev",
    help="Autonomous development improvement agent for Privacy by Design Foundation",
)
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("autodev")


@app.command()
def discover(
    config_dir: Path = typer.Option(
        Path("config"), "--config", "-c", help="Configuration directory"
    ),
    repos_dir: Path = typer.Option(
        Path("repos"), "--repos", "-r", help="Directory containing cloned repositories"
    ),
    output_dir: Path = typer.Option(
        Path("data"), "--output", "-o", help="Output directory for results"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Don't create issues, just analyze"
    ),
) -> None:
    """Discover improvement opportunities in target repositories."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load configuration
    config = load_config(config_dir)
    logger.info(f"Loaded configuration for {len(config.repositories)} repositories")

    # Fetch sources
    logger.info("Fetching monitored sources...")
    fetcher = SourceFetcher(config.sources)
    sources_data = fetcher.fetch_all()
    sources_path = output_dir / "sources.json"
    sources_path.write_text(json.dumps(sources_data, indent=2))
    logger.info(f"Saved source data to {sources_path}")

    # Analyze repositories
    logger.info("Analyzing repositories...")
    analyzer = RepositoryAnalyzer(config)
    analysis = analyzer.analyze(repos_dir, sources_data)
    analysis_path = output_dir / "analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2))
    logger.info(f"Saved analysis to {analysis_path}")

    # Generate proposals
    logger.info("Generating improvement proposals...")
    generator = ProposalGenerator(config)
    proposals = generator.generate(analysis)
    proposals_path = output_dir / "proposals.json"
    proposals_path.write_text(json.dumps(proposals, indent=2))
    logger.info(f"Generated {len(proposals)} proposals")

    if dry_run:
        console.print("\n[yellow]Dry run mode - no issues created[/yellow]")
        for proposal in proposals:
            console.print(f"  - [{proposal['repo']}] {proposal['title']}")
    else:
        # Create issues
        logger.info("Creating GitHub issues...")
        creator = IssueCreator()
        created = creator.create_all(proposals)
        logger.info(f"Created {len(created)} issues")


@app.command()
def implement(
    issue_repo: str = typer.Argument(..., help="Repository (owner/name)"),
    issue_number: int = typer.Argument(..., help="Issue number"),
    repo_path: Path = typer.Option(
        Path("target-repo"), "--repo", "-r", help="Path to cloned repository"
    ),
    config_dir: Path = typer.Option(
        Path("config"), "--config", "-c", help="Configuration directory"
    ),
) -> None:
    """Implement an approved issue."""
    config = load_config(config_dir)

    implementer = Implementer(config)
    result = implementer.implement(
        repo=issue_repo,
        issue_number=issue_number,
        repo_path=repo_path,
    )

    if result.success:
        console.print(f"[green]Successfully implemented issue #{issue_number}[/green]")
        console.print(f"Branch: {result.branch_name}")
        console.print(f"Commit: {result.commit_sha}")
    else:
        console.print(f"[red]Failed to implement issue #{issue_number}[/red]")
        console.print(f"Error: {result.error}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show status of pending AutoDev issues and PRs."""
    from autodev.issues.find_approved import find_approved_issues
    from autodev.tracking import get_tracking_status

    repos = [
        "privacybydesign/irmago",
        "privacybydesign/irmamobile",
        "privacybydesign/pbdf-schememanager",
    ]

    console.print("\n[bold]AutoDev Agent Status[/bold]\n")

    for repo in repos:
        console.print(f"[cyan]{repo}[/cyan]")
        status = get_tracking_status(repo)
        console.print(f"  Proposals pending: {status['pending']}")
        console.print(f"  Approved: {status['approved']}")
        console.print(f"  PRs in review: {status['prs_open']}")
        console.print(f"  Merged: {status['merged']}")
        console.print()


if __name__ == "__main__":
    app()
