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
- [pbdf-schememanager](https://github.com/privacybydesign/pbdf-schememanager) - Credential definitions and issuer info

## Monitored Sources

- [Age Verification Dev](https://ageverification.dev/) - EU Age Verification standards
- [EUDI Wallet ARF](https://eudi.dev/) - European Digital Identity Wallet specifications
- [eIDAS 2.0 specifications](https://digital-strategy.ec.europa.eu/en/policies/eidas-regulation)

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
- `config/irmago.yaml` - irmago improvement rules
- `config/irmamobile.yaml` - irmamobile improvement rules
- `config/pbdf-schememanager.yaml` - pbdf-schememanager improvement rules
- `config/sources.yaml` - Monitored source URLs and parsing rules

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
