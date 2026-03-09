# AutoDev Agent

An autonomous development agent that monitors privacy and digital identity standards, proposes incremental improvements to the Privacy by Design Foundation repositories, and creates draft PRs for approved issues.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) - applying autonomous agent principles to software development improvement.

## Overview

AutoDev runs nightly via GitHub Actions to:

1. **Monitor Sources**: Track updates from EU digital identity standards and specifications
2. **Analyze Repositories**: Identify improvement opportunities in target codebases
3. **Create Issues**: Propose small, incremental improvements for human approval
4. **Implement Changes**: Create draft PRs for approved issues with maintainable, tested code

## Target Repositories

- [irmago](https://github.com/privacybydesign/irmago) - IRMA/Yivi server, client, and tooling (Go)
- [irmamobile](https://github.com/privacybydesign/irmamobile) - Yivi app for iOS and Android (Dart/Flutter)

## Focus Areas

The agent specifically looks for:

### Missing Protocols
- **OpenID4VCI** - Credential issuance protocol
- **OpenID4VP** - Credential presentation protocol
- **SIOPv2** - Self-Issued OpenID Provider
- **ISO 18013-5** - mDL device retrieval
- **OID4IDA** - Identity assurance

### Missing Credential Formats
- **SD-JWT** - Selective Disclosure JWT
- **mdoc/mDL** - ISO 18013-5 mobile documents
- **W3C Verifiable Credentials** - VC Data Model 2.0
- **JWT-VC** - JWT-encoded Verifiable Credentials

## Monitored Sources

### Standards & Specifications
- [Age Verification Dev](https://ageverification.dev/) - EU Age Verification standards
- [EUDI Wallet ARF](https://eudi.dev/) - European Digital Identity Wallet specifications
- [eIDAS 2.0](https://digital-strategy.ec.europa.eu/en/policies/eidas-regulation)

### Protocol Specifications
- [OpenID4VCI](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html)
- [OpenID4VP](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html)
- [SIOPv2](https://openid.net/specs/openid-connect-self-issued-v2-1_0.html)

### Credential Format Specifications
- [SD-JWT](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt)
- [W3C VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Nightly)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │   Monitor    │   │   Analyze    │   │   Propose Issues     │ │
│  │   Sources    │──▶│   Repos      │──▶│   (Human Approval)   │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                                                                  │
│                           ▼ (approved)                           │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │   Create     │   │   Run        │   │   Create Draft PR    │ │
│  │   Branch     │──▶│   Tests      │──▶│   (Human Review)     │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow

### Phase 1: Issue Discovery (Nightly)
1. Fetch latest updates from monitored sources
2. Analyze target repositories for:
   - Standards compliance gaps
   - Testing coverage improvements
   - Documentation updates
   - Code quality enhancements
   - Security improvements
3. Create GitHub issues with `autodev-proposal` label
4. Update tracking issue with daily summary

### Phase 2: Implementation (Nightly, for approved issues)
1. Find issues labeled `autodev-approved`
2. Create feature branch
3. Implement changes with tests
4. Run test suite
5. Create draft PR linked to issue
6. Add `autodev-draft` label for human review

## Labels

| Label | Description |
|-------|-------------|
| `autodev-proposal` | Issue proposed by AutoDev, awaiting human approval |
| `autodev-approved` | Human-approved issue, ready for implementation |
| `autodev-draft` | Draft PR created by AutoDev, awaiting review |
| `autodev-tracking` | Meta-issue tracking all AutoDev activity |

## Configuration

See `config/` for repository-specific settings:
- `config/sources.yaml` - Monitored sources (protocols, credential formats, standards)
- `config/irmago.yaml` - irmago protocol/format improvement rules
- `config/irmamobile.yaml` - irmamobile UI/UX improvement rules

## Setup

1. Fork this repository to the Privacy by Design Foundation organization
2. Configure repository secrets:
   - `ANTHROPIC_API_KEY` - For Claude Code agent
   - `GH_PAT` - GitHub Personal Access Token with repo access
3. Enable GitHub Actions
4. Create initial tracking issue in each target repository

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m autodev.main --dry-run

# Run tests
pytest tests/
```

## Principles

Adapted from autoresearch:

1. **Small, Incremental Changes**: Each improvement should be reviewable in < 10 minutes
2. **Always Test**: Every code change must include appropriate tests
3. **Never Break Builds**: Changes must pass CI before PR creation
4. **Human Approval Required**: No changes merged without human review
5. **Transparent Tracking**: All activity logged in tracking issue

## License

MIT License - See [LICENSE](LICENSE)
