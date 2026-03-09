"""Tests for existing work detection."""

import pytest

from autodev.existing_work import (
    ExistingWork,
    _extract_keywords,
    format_existing_work_context,
    is_duplicate_proposal,
)


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_extracts_protocol_keywords(self):
        """Should extract protocol-related keywords."""
        text = "Add OpenID4VCI credential offer endpoint"
        keywords = _extract_keywords(text)
        assert "openid4vci" in keywords

    def test_extracts_age_verification_keywords(self):
        """Should extract age verification keywords."""
        text = "Implement age-verification flow"
        keywords = _extract_keywords(text)
        assert "ageverification" in keywords

    def test_extracts_multiple_keywords(self):
        """Should extract multiple keywords."""
        text = "Add SD-JWT support for OpenID4VP"
        keywords = _extract_keywords(text)
        assert "sdjwt" in keywords
        assert "openid4vp" in keywords

    def test_handles_variations(self):
        """Should handle keyword variations."""
        text1 = "openid4vci support"
        text2 = "oid4vci support"
        text3 = "openid-4-vci support"

        assert "openid4vci" in _extract_keywords(text1)
        assert "oid4vci" in _extract_keywords(text2)

    def test_case_insensitive(self):
        """Should be case insensitive."""
        text = "OPENID4VCI and SIOPv2"
        keywords = _extract_keywords(text)
        assert "openid4vci" in keywords
        assert "siopv2" in keywords or "siop" in keywords


class TestIsDuplicateProposal:
    """Tests for duplicate detection."""

    @pytest.fixture
    def existing_work(self):
        """Create sample existing work."""
        return ExistingWork(
            open_issues=[
                {"number": 123, "title": "Add OpenID4VCI support"},
                {"number": 124, "title": "Implement age verification flow"},
            ],
            open_prs=[
                {"number": 200, "title": "WIP: SD-JWT credential format"},
            ],
            recent_commits=[
                {"sha": "abc123", "message": "Start OpenID4VP implementation"},
            ],
            in_progress_keywords={"openid4vci", "openid4vp", "sdjwt", "ageverification"},
        )

    def test_detects_duplicate_issue(self, existing_work):
        """Should detect proposal that duplicates an issue."""
        is_dup, reason = is_duplicate_proposal(
            "Implement OpenID4VCI credential issuance",
            existing_work,
        )
        assert is_dup is True
        assert "123" in reason

    def test_detects_duplicate_pr(self, existing_work):
        """Should detect proposal that duplicates a PR."""
        is_dup, reason = is_duplicate_proposal(
            "Add SD-JWT support",
            existing_work,
        )
        assert is_dup is True
        assert "200" in reason

    def test_detects_active_work(self, existing_work):
        """Should detect topics in active development."""
        is_dup, reason = is_duplicate_proposal(
            "OpenID4VCI and OpenID4VP integration",
            existing_work,
        )
        assert is_dup is True
        assert "active development" in reason.lower()

    def test_allows_unrelated_proposal(self, existing_work):
        """Should allow proposals that don't duplicate."""
        is_dup, reason = is_duplicate_proposal(
            "Add documentation for API endpoints",
            existing_work,
        )
        assert is_dup is False
        assert reason is None

    def test_allows_different_protocol(self, existing_work):
        """Should allow proposals for different protocols."""
        is_dup, reason = is_duplicate_proposal(
            "Implement ISO 18013-5 mdoc support",
            existing_work,
        )
        # mdoc is not in the existing work keywords
        assert is_dup is False


class TestFormatExistingWorkContext:
    """Tests for formatting existing work."""

    def test_formats_issues(self):
        """Should format open issues."""
        existing = ExistingWork(
            open_issues=[
                {"number": 1, "title": "Test issue", "labels": ["bug"]},
            ],
            open_prs=[],
            recent_commits=[],
            in_progress_keywords=set(),
        )

        context = format_existing_work_context(existing)

        assert "Open Issues" in context
        assert "#1" in context
        assert "Test issue" in context

    def test_formats_prs(self):
        """Should format open PRs."""
        existing = ExistingWork(
            open_issues=[],
            open_prs=[
                {"number": 10, "title": "Add feature", "draft": True},
            ],
            recent_commits=[],
            in_progress_keywords=set(),
        )

        context = format_existing_work_context(existing)

        assert "Pull Requests" in context
        assert "#10" in context
        assert "DRAFT" in context

    def test_formats_keywords(self):
        """Should format in-progress keywords."""
        existing = ExistingWork(
            open_issues=[],
            open_prs=[],
            recent_commits=[],
            in_progress_keywords={"openid4vci", "sdjwt"},
        )

        context = format_existing_work_context(existing)

        assert "work in progress" in context.lower()
        assert "openid4vci" in context
        assert "sdjwt" in context

    def test_empty_existing_work(self):
        """Should handle empty existing work."""
        existing = ExistingWork(
            open_issues=[],
            open_prs=[],
            recent_commits=[],
            in_progress_keywords=set(),
        )

        context = format_existing_work_context(existing)

        # Should return empty or minimal string
        assert isinstance(context, str)
