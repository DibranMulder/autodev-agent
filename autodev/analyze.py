"""Analyze repositories for improvement opportunities."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from autodev.config import AutoDevConfig, get_repo_config
from autodev.existing_work import (
    ExistingWork,
    check_existing_work,
    format_existing_work_context,
    is_duplicate_proposal,
)
from autodev.llm import query_llm, extract_json, get_llm_backend

logger = logging.getLogger(__name__)

# Specific interoperability requirements from EU Age Verification Blueprint
EU_AV_INTEROP_REQUIREMENTS = """
## EU Age Verification Interoperability Requirements

The EU Age Verification solution (ageverification.dev) defines these MANDATORY requirements
for wallet interoperability:

### 1. CREDENTIAL FORMAT (eu.europa.ec.av.1)
- **DocType**: `eu.europa.ec.av.1`
- **Namespace**: `eu.europa.ec.av.1`
- **Required attribute**: `age_over_18` (boolean, MANDATORY)
- **Optional attributes**: `age_over_NN` for other thresholds (21, 65, etc.)
- **Primary format**: mdoc (ISO/IEC 18013-5)
- **Alternative format**: SD-JWT VC (per HAIP profile)
- **Validity period**: Maximum 3 months from issuance
- **Batch issuance**: 30 attestations per batch recommended
- **No additional attributes permitted** (privacy by design)

### 2. ISSUANCE PROTOCOL (OpenID4VCI)
- Pre-authorized code flow for out-of-band identity verification
- Wallet attestation authentication required
- Batch credential issuance support
- Device key binding through MSO (Mobile Security Object)

### 3. PRESENTATION PROTOCOL (OpenID4VP)
- Same-device presentation flow
- Cross-device presentation flow (QR code)
- Single-use attestation enforcement
- User authentication before presentation (PIN/biometric)

### 4. TRUST FRAMEWORK
- ETSI trusted list validation (ETSI TS 119 612)
- Trust anchor: https://eidas.ec.europa.eu/efda/trust-services/browse/av-tl
- Attestation provider certificate validation
- QTSP or provider-operated PKI certificates

### 5. DEVICE SECURITY
- Secure Enclave (iOS) / TEE/Strongbox (Android) key storage
- Hardware-backed cryptographic operations
- Single-use tracking to prevent attestation reuse

### 6. ZERO-KNOWLEDGE PROOFS (Optional, Annex B)
- zkSNARK-based age verification
- Prove age_over_X without revealing birthdate
- Backward-compatible with standard presentation
"""

SYSTEM_PROMPT = f"""You are an expert in digital identity interoperability, analyzing the IRMA/Yivi repositories for compatibility with the EU Age Verification Blueprint.

{EU_AV_INTEROP_REQUIREMENTS}

## YOUR TASK
Identify SPECIFIC gaps that prevent IRMA/Yivi from interoperating with EU Age Verification issuers and verifiers.

## RULES
1. **Focus on INTEROPERABILITY** - What's missing to work with EU AV infrastructure?
2. **Be SPECIFIC** - Reference exact doctype, namespace, attribute names
3. **Check existing work** - Don't propose duplicates
4. **Prioritize by impact** - What blocks interoperability vs. nice-to-have?

## Output Format
Return JSON:
{{
    "summary": "Interoperability assessment summary",
    "interop_status": {{
        "credential_format_eu_av_1": "not_supported|partial|full",
        "openid4vci_issuance": "not_supported|partial|full",
        "openid4vp_presentation": "not_supported|partial|full",
        "etsi_trust_list": "not_supported|partial|full",
        "batch_issuance": "not_supported|partial|full",
        "device_security": "not_supported|partial|full"
    }},
    "existing_work_acknowledged": ["list of relevant issues/PRs"],
    "opportunities": [
        {{
            "category": "age_verification_interop|protocols|credential_formats",
            "title": "Specific interop gap title",
            "description": "Detailed description with EU AV spec references",
            "interop_impact": "critical|high|medium - why this blocks interop",
            "files_affected": ["files"],
            "priority": 1-5,
            "effort": "small|medium|large",
            "spec_reference": "ageverification.dev section or annex",
            "not_duplicate_because": "reason"
        }}
    ]
}}"""


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
            "focus": "EU Age Verification Interoperability",
            "repositories": {},
        }

        for repo_config in self.config.repositories:
            repo_path = repos_dir / repo_config.name
            if not repo_path.exists():
                logger.warning(f"Repository {repo_config.name} not found at {repo_path}")
                continue

            full_repo_name = f"{repo_config.owner}/{repo_config.name}"

            # Check for existing work FIRST
            logger.info(f"Checking existing work in {full_repo_name}...")
            existing_work = check_existing_work(full_repo_name, repo_path)

            logger.info(f"Analyzing {repo_config.name} for EU AV interoperability...")
            analysis = self._analyze_repository(
                repo_path, repo_config, sources_data, existing_work
            )

            # Filter out duplicates
            if "opportunities" in analysis:
                filtered = []
                for opp in analysis["opportunities"]:
                    is_dup, reason = is_duplicate_proposal(opp.get("title", ""), existing_work)
                    if is_dup:
                        logger.info(f"Filtered duplicate: {opp.get('title')} - {reason}")
                    else:
                        filtered.append(opp)
                analysis["opportunities"] = filtered

            results["repositories"][repo_config.name] = analysis

        return results

    def _analyze_repository(
        self,
        repo_path: Path,
        repo_config: Any,
        sources_data: dict[str, Any],
        existing_work: ExistingWork,
    ) -> dict[str, Any]:
        """Analyze a single repository."""
        context = self._gather_context(repo_path, repo_config)
        prompt = self._build_analysis_prompt(context, sources_data, repo_config, existing_work)

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
            "age_verification_files": [],
            "credential_format_files": [],
            "protocol_files": [],
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
            for excluded in repo_config.excluded_paths:
                files = [f for f in files if excluded not in f]
            context["structure"] = files[:100]

            # Identify relevant files for interop analysis
            for f in files:
                f_lower = f.lower()
                if any(kw in f_lower for kw in ["age", "av", "verification"]):
                    context["age_verification_files"].append(f)
                if any(kw in f_lower for kw in ["mdoc", "sdjwt", "credential", "format"]):
                    context["credential_format_files"].append(f)
                if any(kw in f_lower for kw in ["openid", "oid4", "vci", "vp", "protocol"]):
                    context["protocol_files"].append(f)

        except Exception as e:
            logger.warning(f"Failed to get structure: {e}")

        # Read README
        for readme_name in ["README.md", "README", "readme.md", "CHANGELOG.md"]:
            readme_path = repo_path / readme_name
            if readme_path.exists():
                content = readme_path.read_text()[:5000]
                if readme_name == "CHANGELOG.md":
                    context["changelog"] = content
                else:
                    context["readme"] = content

        # Get recent commits
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-30"],
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
        existing_work: ExistingWork,
    ) -> str:
        """Build the analysis prompt."""
        existing_work_context = format_existing_work_context(existing_work)

        return f"""Analyze {repo_config.name} for EU Age Verification INTEROPERABILITY gaps.

## Repository: {repo_config.name}
Language: {repo_config.language}

## EXISTING WORK - DO NOT DUPLICATE
{existing_work_context}

## File Structure
{chr(10).join(context['structure'][:40])}

## Potentially Relevant Files
- Age verification: {context.get('age_verification_files', [])}
- Credential formats: {context.get('credential_format_files', [])}
- Protocols: {context.get('protocol_files', [])}

## README
{context.get('readme', 'Not found')[:2000]}

## Recent Commits
{chr(10).join(context['recent_commits'][:15])}

## INTEROPERABILITY CHECKLIST

Check each EU AV requirement and report status:

### 1. Credential Format (eu.europa.ec.av.1)
- [ ] Does it support mdoc with doctype `eu.europa.ec.av.1`?
- [ ] Does it support namespace `eu.europa.ec.av.1`?
- [ ] Does it support `age_over_18` boolean attribute?
- [ ] Does it enforce max 3-month validity?
- [ ] Does it support batch issuance (30 attestations)?

### 2. OpenID4VCI Issuance
- [ ] Is OpenID4VCI implemented? (CHECK EXISTING WORK!)
- [ ] Does it support wallet attestation?
- [ ] Does it support pre-authorized code flow?
- [ ] Does it support batch credential issuance?

### 3. OpenID4VP Presentation
- [ ] Is OpenID4VP implemented?
- [ ] Does it support same-device flow?
- [ ] Does it support cross-device flow?
- [ ] Does it enforce single-use attestations?

### 4. Trust Framework
- [ ] Can it fetch ETSI trusted lists?
- [ ] Can it validate attestation provider certificates?
- [ ] Does it check trust anchor chain?

### 5. Device Security
- [ ] Does it use Secure Enclave/TEE for keys?
- [ ] Does it require user auth before presentation?

## Task
Identify the TOP 3-5 gaps that block EU AV interoperability.
Focus on what's MISSING, not what exists.
Return analysis as JSON."""


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
