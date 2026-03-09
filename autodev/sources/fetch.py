"""Fetch and parse monitored sources."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

from autodev.config import SourceConfig

logger = logging.getLogger(__name__)


class SourceFetcher:
    """Fetch and parse content from monitored sources."""

    def __init__(
        self,
        sources: list[SourceConfig],
        cache_dir: Path | None = None,
    ):
        self.sources = sources
        self.cache_dir = cache_dir or Path.home() / ".cache" / "autodev" / "sources"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "AutoDev-Agent/1.0 (Privacy by Design Foundation)"
            },
        )

    def fetch_all(self) -> dict[str, Any]:
        """Fetch all configured sources."""
        results = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sources": {},
        }

        for source in self.sources:
            try:
                logger.info(f"Fetching {source.name} from {source.url}")
                data = self.fetch_source(source)
                results["sources"][source.name] = data
            except Exception as e:
                logger.error(f"Failed to fetch {source.name}: {e}")
                results["sources"][source.name] = {
                    "error": str(e),
                    "url": source.url,
                }

        return results

    def fetch_source(self, source: SourceConfig) -> dict[str, Any]:
        """Fetch a single source."""
        response = self.client.get(source.url)
        response.raise_for_status()

        content = response.text
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check cache for changes
        cache_file = self.cache_dir / f"{source.name}.json"
        previous_hash = None
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
                previous_hash = cached.get("content_hash")

        changed = previous_hash != content_hash

        # Parse content based on type
        if source.type == "html":
            parsed = self._parse_html(content, source)
        elif source.type == "rss":
            parsed = self._parse_rss(content, source)
        elif source.type == "github":
            parsed = self._parse_github(content, source)
        else:
            parsed = {"raw": content[:10000]}

        result = {
            "url": source.url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
            "changed_since_last": changed,
            "content": parsed,
        }

        # Update cache
        with open(cache_file, "w") as f:
            json.dump(result, f, indent=2)

        return result

    def _parse_html(self, content: str, source: SourceConfig) -> dict[str, Any]:
        """Parse HTML content."""
        soup = BeautifulSoup(content, "lxml")

        # Remove scripts and styles
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()

        result: dict[str, Any] = {}

        # Extract based on selectors if provided
        if source.selectors:
            for key, selector in source.selectors.items():
                elements = soup.select(selector)
                if elements:
                    result[key] = [
                        markdownify(str(el), strip=["a"])
                        for el in elements
                    ]
        else:
            # Extract main content
            main = soup.find("main") or soup.find("article") or soup.find("body")
            if main:
                result["main_content"] = markdownify(str(main), strip=["a"])[:20000]

        # Extract headings for structure
        headings = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            headings.append({
                "level": int(h.name[1]),
                "text": h.get_text(strip=True),
            })
        result["headings"] = headings

        # Extract links to specs/docs
        spec_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if any(kw in href.lower() or kw in text.lower()
                   for kw in ["spec", "doc", "standard", "rfc", "eidas", "arf"]):
                spec_links.append({"text": text, "href": href})
        result["spec_links"] = spec_links[:20]

        return result

    def _parse_rss(self, content: str, source: SourceConfig) -> dict[str, Any]:
        """Parse RSS/Atom feed."""
        soup = BeautifulSoup(content, "lxml-xml")

        items = []
        for item in soup.find_all(["item", "entry"])[:20]:
            title = item.find("title")
            link = item.find("link")
            published = item.find(["pubDate", "published", "updated"])
            description = item.find(["description", "summary", "content"])

            items.append({
                "title": title.get_text(strip=True) if title else None,
                "link": link.get("href") or link.get_text(strip=True) if link else None,
                "published": published.get_text(strip=True) if published else None,
                "description": description.get_text(strip=True)[:500] if description else None,
            })

        return {"items": items}

    def _parse_github(self, content: str, source: SourceConfig) -> dict[str, Any]:
        """Parse GitHub API response or page."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._parse_html(content, source)


def main():
    """CLI entry point for source fetching."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import yaml
    with open(args.config) as f:
        config_data = yaml.safe_load(f)

    sources = [SourceConfig(**s) for s in config_data.get("sources", [])]
    fetcher = SourceFetcher(sources)
    results = fetcher.fetch_all()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
