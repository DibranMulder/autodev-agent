"""Tests for proposal generation."""

import pytest

from autodev.config import AutoDevConfig, ImprovementCategory, RepositoryConfig
from autodev.propose import ProposalGenerator


@pytest.fixture
def config():
    """Create test configuration."""
    return AutoDevConfig(
        repositories=[
            RepositoryConfig(name="irmago", language="Go"),
        ],
        categories=[
            ImprovementCategory(name="testing", priority=1, max_per_day=2),
            ImprovementCategory(name="security", priority=1, max_per_day=1),
        ],
        max_issues_per_day=5,
    )


@pytest.fixture
def generator(config: AutoDevConfig):
    """Create proposal generator."""
    return ProposalGenerator(config)


def test_generate_proposals(generator: ProposalGenerator):
    """Test generating proposals from analysis."""
    analysis = {
        "repositories": {
            "irmago": {
                "summary": "Test summary",
                "opportunities": [
                    {
                        "category": "testing",
                        "title": "Add unit tests for session handler",
                        "description": "The session handler lacks tests",
                        "files_affected": ["session/handler.go"],
                        "priority": 1,
                        "effort": "small",
                        "rationale": "Improve test coverage",
                    },
                    {
                        "category": "security",
                        "title": "Add input validation",
                        "description": "Validate API inputs",
                        "files_affected": ["api/server.go"],
                        "priority": 1,
                        "effort": "medium",
                        "rationale": "Security improvement",
                    },
                ],
            }
        }
    }

    proposals = generator.generate(analysis)

    assert len(proposals) == 2
    assert proposals[0]["repo"] == "privacybydesign/irmago"
    assert "[AutoDev]" in proposals[0]["title"]
    assert "autodev-proposal" in proposals[0]["labels"]


def test_respects_category_limits(generator: ProposalGenerator):
    """Test that category limits are respected."""
    analysis = {
        "repositories": {
            "irmago": {
                "opportunities": [
                    {"category": "testing", "title": "Test 1", "priority": 1},
                    {"category": "testing", "title": "Test 2", "priority": 2},
                    {"category": "testing", "title": "Test 3", "priority": 3},
                ],
            }
        }
    }

    proposals = generator.generate(analysis)

    # Only 2 testing proposals should be generated (max_per_day=2)
    assert len(proposals) == 2


def test_respects_daily_limit(config: AutoDevConfig):
    """Test that daily issue limit is respected."""
    config.max_issues_per_day = 2
    generator = ProposalGenerator(config)

    analysis = {
        "repositories": {
            "irmago": {
                "opportunities": [
                    {"category": "testing", "title": "Test 1", "priority": 1},
                    {"category": "testing", "title": "Test 2", "priority": 2},
                    {"category": "security", "title": "Security 1", "priority": 1},
                ],
            }
        }
    }

    proposals = generator.generate(analysis)

    assert len(proposals) == 2


def test_skips_disabled_categories(config: AutoDevConfig):
    """Test that disabled categories are skipped."""
    config.categories[0].enabled = False  # Disable testing
    generator = ProposalGenerator(config)

    analysis = {
        "repositories": {
            "irmago": {
                "opportunities": [
                    {"category": "testing", "title": "Test 1", "priority": 1},
                    {"category": "security", "title": "Security 1", "priority": 1},
                ],
            }
        }
    }

    proposals = generator.generate(analysis)

    # Only security proposal should be generated
    assert len(proposals) == 1
    assert "security" in proposals[0]["category"]


def test_proposal_body_format(generator: ProposalGenerator):
    """Test that proposal body is properly formatted."""
    analysis = {
        "repositories": {
            "irmago": {
                "opportunities": [
                    {
                        "category": "testing",
                        "title": "Add tests",
                        "description": "Add comprehensive tests",
                        "rationale": "Better coverage",
                        "files_affected": ["test.go"],
                        "priority": 1,
                        "effort": "small",
                    },
                ],
            }
        }
    }

    proposals = generator.generate(analysis)

    body = proposals[0]["body"]
    assert "## Description" in body
    assert "## Rationale" in body
    assert "## Files Affected" in body
    assert "test.go" in body
    assert "autodev-approved" in body


def test_handles_analysis_errors(generator: ProposalGenerator):
    """Test handling of analysis with errors."""
    analysis = {
        "repositories": {
            "irmago": {
                "error": "Analysis failed",
            }
        }
    }

    proposals = generator.generate(analysis)

    assert len(proposals) == 0
