"""Tests for configuration loading."""

from pathlib import Path

import pytest

from autodev.config import (
    AutoDevConfig,
    ImprovementCategory,
    RepositoryConfig,
    SourceConfig,
    get_repo_config,
    load_config,
)


def test_source_config():
    """Test SourceConfig model."""
    config = SourceConfig(
        name="test",
        url="https://example.com",
        type="html",
    )
    assert config.name == "test"
    assert config.url == "https://example.com"
    assert config.type == "html"
    assert config.update_frequency == "daily"


def test_repository_config():
    """Test RepositoryConfig model."""
    config = RepositoryConfig(
        name="testrepo",
        language="Go",
        test_command="go test ./...",
    )
    assert config.name == "testrepo"
    assert config.owner == "privacybydesign"
    assert config.language == "Go"
    assert config.focus_areas == []


def test_improvement_category():
    """Test ImprovementCategory model."""
    category = ImprovementCategory(
        name="testing",
        priority=1,
        max_per_day=3,
    )
    assert category.name == "testing"
    assert category.enabled is True
    assert category.priority == 1
    assert category.max_per_day == 3


def test_autodev_config_defaults():
    """Test AutoDevConfig defaults."""
    config = AutoDevConfig()
    assert config.sources == []
    assert config.repositories == []
    assert config.max_issues_per_day == 5
    assert config.max_prs_per_day == 3


def test_get_repo_config():
    """Test getting repository config by name."""
    config = AutoDevConfig(
        repositories=[
            RepositoryConfig(name="irmago", language="Go"),
            RepositoryConfig(name="irmamobile", language="Dart"),
        ]
    )

    irmago = get_repo_config(config, "irmago")
    assert irmago is not None
    assert irmago.language == "Go"

    missing = get_repo_config(config, "nonexistent")
    assert missing is None


def test_load_config(tmp_path: Path):
    """Test loading config from directory."""
    # Create sources.yaml
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text("""
sources:
  - name: test_source
    url: https://example.com
    type: html

categories:
  - name: testing
    enabled: true
    priority: 1
    max_per_day: 2
""")

    # Create repo config
    repo_yaml = tmp_path / "testrepo.yaml"
    repo_yaml.write_text("""
repository:
  name: testrepo
  language: Go
  test_command: go test ./...
""")

    config = load_config(tmp_path)

    assert len(config.sources) == 1
    assert config.sources[0].name == "test_source"

    assert len(config.categories) == 1
    assert config.categories[0].name == "testing"

    assert len(config.repositories) == 1
    assert config.repositories[0].name == "testrepo"
