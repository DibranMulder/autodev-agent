"""Tests for source fetching."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from autodev.config import SourceConfig
from autodev.sources.fetch import SourceFetcher


@pytest.fixture
def source_config():
    """Create test source config."""
    return SourceConfig(
        name="test_source",
        url="https://example.com/specs",
        type="html",
        selectors={"headings": "h1, h2"},
    )


@pytest.fixture
def fetcher(tmp_path: Path, source_config: SourceConfig):
    """Create fetcher with test cache."""
    return SourceFetcher(
        sources=[source_config],
        cache_dir=tmp_path / "cache",
    )


def test_fetch_html_source(fetcher: SourceFetcher, source_config: SourceConfig):
    """Test fetching HTML source."""
    html_content = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Main Title</h1>
            <h2>Section 1</h2>
            <p>Content here</p>
            <a href="/spec/v1">Specification v1</a>
        </body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status = MagicMock()

    with patch.object(fetcher.client, "get", return_value=mock_response):
        result = fetcher.fetch_source(source_config)

    assert result["url"] == "https://example.com/specs"
    assert "content_hash" in result
    assert "headings" in result["content"]
    assert len(result["content"]["headings"]) == 2


def test_fetch_all_sources(fetcher: SourceFetcher):
    """Test fetching all configured sources."""
    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test</h1></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch.object(fetcher.client, "get", return_value=mock_response):
        results = fetcher.fetch_all()

    assert "fetched_at" in results
    assert "sources" in results
    assert "test_source" in results["sources"]


def test_fetch_detects_changes(fetcher: SourceFetcher, source_config: SourceConfig):
    """Test that fetcher detects content changes."""
    # First fetch
    mock_response1 = MagicMock()
    mock_response1.text = "<html><body><h1>Version 1</h1></body></html>"
    mock_response1.raise_for_status = MagicMock()

    with patch.object(fetcher.client, "get", return_value=mock_response1):
        result1 = fetcher.fetch_source(source_config)
    assert result1["changed_since_last"] is True

    # Second fetch with same content
    with patch.object(fetcher.client, "get", return_value=mock_response1):
        result2 = fetcher.fetch_source(source_config)
    assert result2["changed_since_last"] is False

    # Third fetch with different content
    mock_response2 = MagicMock()
    mock_response2.text = "<html><body><h1>Version 2</h1></body></html>"
    mock_response2.raise_for_status = MagicMock()

    with patch.object(fetcher.client, "get", return_value=mock_response2):
        result3 = fetcher.fetch_source(source_config)
    assert result3["changed_since_last"] is True


def test_fetch_handles_errors(fetcher: SourceFetcher):
    """Test error handling during fetch."""
    with patch.object(
        fetcher.client,
        "get",
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        ),
    ):
        results = fetcher.fetch_all()

    assert "error" in results["sources"]["test_source"]


def test_parse_html_extracts_spec_links(fetcher: SourceFetcher, source_config: SourceConfig):
    """Test that spec links are extracted from HTML."""
    html = """
    <html>
        <body>
            <a href="/spec/v1.pdf">Specification</a>
            <a href="/docs/standard.html">Standard Doc</a>
            <a href="/about">About Us</a>
            <a href="/rfc/123">RFC 123</a>
        </body>
    </html>
    """

    result = fetcher._parse_html(html, source_config)

    assert "spec_links" in result
    # Should extract links containing spec, standard, rfc
    spec_hrefs = [link["href"] for link in result["spec_links"]]
    assert "/spec/v1.pdf" in spec_hrefs
    assert "/docs/standard.html" in spec_hrefs
    assert "/rfc/123" in spec_hrefs
    assert "/about" not in spec_hrefs
