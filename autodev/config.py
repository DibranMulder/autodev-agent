"""Configuration management for AutoDev Agent."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for a monitored source."""

    name: str
    url: str
    type: str = "html"  # html, rss, github
    selectors: dict[str, str] = Field(default_factory=dict)
    update_frequency: str = "daily"


class RepositoryConfig(BaseModel):
    """Configuration for a target repository."""

    name: str
    owner: str = "privacybydesign"
    language: str
    test_command: str | None = None
    lint_command: str | None = None
    focus_areas: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)


class ImprovementCategory(BaseModel):
    """Category of improvements to look for."""

    name: str
    enabled: bool = True
    priority: int = 1  # 1 = highest
    max_per_day: int = 3
    prompt_template: str = ""


class AutoDevConfig(BaseModel):
    """Main configuration for AutoDev Agent."""

    sources: list[SourceConfig] = Field(default_factory=list)
    repositories: list[RepositoryConfig] = Field(default_factory=list)
    categories: list[ImprovementCategory] = Field(default_factory=list)
    tracking_repo: str = "privacybydesign/autodev-agent"
    max_issues_per_day: int = 5
    max_prs_per_day: int = 3


def load_config(config_dir: Path) -> AutoDevConfig:
    """Load configuration from YAML files in config directory."""
    sources_file = config_dir / "sources.yaml"
    repositories: list[RepositoryConfig] = []
    sources: list[SourceConfig] = []
    categories: list[ImprovementCategory] = []

    # Load sources
    if sources_file.exists():
        with open(sources_file) as f:
            data = yaml.safe_load(f)
            sources = [SourceConfig(**s) for s in data.get("sources", [])]
            categories = [
                ImprovementCategory(**c) for c in data.get("categories", [])
            ]

    # Load repository configs
    for repo_file in config_dir.glob("*.yaml"):
        if repo_file.name == "sources.yaml":
            continue
        with open(repo_file) as f:
            data = yaml.safe_load(f)
            if "repository" in data:
                repositories.append(RepositoryConfig(**data["repository"]))

    return AutoDevConfig(
        sources=sources,
        repositories=repositories,
        categories=categories,
    )


def get_repo_config(
    config: AutoDevConfig, repo_name: str
) -> RepositoryConfig | None:
    """Get configuration for a specific repository."""
    for repo in config.repositories:
        if repo.name == repo_name:
            return repo
    return None
