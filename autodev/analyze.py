"""Analyze repositories for improvement opportunities."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from autodev.config import AutoDevConfig, get_repo_config
from autodev.llm import query_llm, extract_json, get_llm_backend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert in digital identity protocols and credential formats, analyzing repositories for the Privacy by Design Foundation (IRMA/Yivi project).

Your PRIMARY goal is to identify missing or incomplete support for:

## Protocols to look for:
- OpenID4VCI (Verifiable Credential Issuance) - credential offer, authorization, token, credential endpoints
- OpenID4VP (Verifiable Presentations) - presentation definition, submission, response
- SIOPv2 (Self-Issued OpenID Provider) - wallet authentication
- ISO 18013-5 (mDL) - device retrieval, session establishment
- OID4IDA (Identity Assurance) - verified claims, assurance levels

## Credential Formats to look for:
- SD-JWT (Selective Disclosure JWT) - disclosures, key binding
- mdoc/mDL (ISO 18013-5) - CBOR encoding, device authentication
- W3C Verifiable Credentials 2.0 - JSON-LD, proof formats
- JWT-VC - JWT-encoded verifiable credentials

For each gap found, propose a small, incremental improvement that:
1. Adds ONE specific protocol endpoint or credential format feature
2. Includes tests for the new functionality
3. Is implementable in a single PR

Output your analysis as JSON with the structure:
{
    "summary": "Brief overview of current protocol/format support",
    "opportunities": [
        {
            "category": "protocols|credential_formats|testing|security|standards_compliance",
            "title": "Short title (e.g., 'Add OpenID4VCI credential offer endpoint')",
            "description": "Detailed description including spec references",
            "files_affected": ["list of files to modify or create"],
            "priority": 1-5 (1 highest),
            "effort": "small|medium|large",
            "rationale": "Why this is needed for EUDI/eIDAS compliance",
            "spec_reference": "Link or section reference to the relevant specification"
        }
    ]
}"""


class RepositoryAnalyzer:
    """Analyze repositories using Claude to find improvement opportunities."""

    def __init__(self, config: AutoDevConfig):
        self.config = config

    def analyze(
        self,
        repos_dir: Path,
        sources_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze all repositories for improvements."""
        from datetime import datetime, timezone

        results = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "llm_backend": get_llm_backend(),
            "repositories": {},
        }

        for repo_config in self.config.repositories:
            repo_path = repos_dir / repo_config.name
            if not repo_path.exists():
                logger.warning(f"Repository {repo_config.name} not found at {repo_path}")
                continue

            logger.info(f"Analyzing {repo_config.name} using {get_llm_backend()} backend...")
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

        # Query LLM
        response = query_llm(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=4096,
        )

        if not response.success:
            logger.error(f"LLM query failed: {response.error}")
            return {
                "summary": "Analysis failed",
                "opportunities": [],
                "error": response.error,
            }

        # Parse response
        result = extract_json(response.content)

        if result is None:
            logger.error("Failed to parse JSON from LLM response")
            return {
                "summary": "Analysis failed - invalid JSON response",
                "opportunities": [],
                "error": "Failed to parse JSON",
                "raw_response": response.content[:2000],
            }

        return result

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

        return f"""Analyze this repository for MISSING PROTOCOLS and CREDENTIAL FORMATS.

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

## CRITICAL: Protocol & Credential Format Analysis

Search the codebase for implementations of:

### Protocols (check if present/complete):
1. **OpenID4VCI**: Look for credential_offer, authorization endpoint, token endpoint, credential endpoint
2. **OpenID4VP**: Look for presentation_definition, vp_token, presentation_submission
3. **SIOPv2**: Look for self-issued ID token, subject_syntax_types_supported
4. **ISO 18013-5**: Look for mdoc, device retrieval, session transcript
5. **OID4IDA**: Look for verified_claims, assurance_level

### Credential Formats (check if present/complete):
1. **SD-JWT**: Look for _sd, _sd_alg, disclosures, kb-jwt
2. **mdoc**: Look for CBOR, IssuerSigned, DeviceSigned, DocType
3. **W3C VC**: Look for @context, verifiableCredential, proof
4. **JWT-VC**: Look for vc claim in JWT, credentialSubject

## Task
Identify 3-5 SPECIFIC missing protocol endpoints or credential format features.
Each should be:
- A single, well-defined addition (not "implement all of OpenID4VCI")
- Testable with unit and integration tests
- Referenced to specific spec sections

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
