#!/usr/bin/env python3
"""Create initial tracking issues in target repositories."""

import os
import sys

from github import Github

TRACKING_ISSUE_TITLE = "[AutoDev] Activity Tracking"
TRACKING_ISSUE_BODY = """## AutoDev Agent Activity Tracking

This issue tracks all AutoDev Agent activity for this repository.

### How It Works

1. **Nightly Discovery** (2 AM UTC): AutoDev analyzes this repository and creates proposal issues with the `autodev-proposal` label
2. **Human Review**: Maintainers review proposals and approve by adding the `autodev-approved` label
3. **Nightly Implementation** (4 AM UTC): AutoDev implements approved issues and creates draft PRs
4. **Human Review**: Maintainers review and merge draft PRs

### Labels

| Label | Meaning |
|-------|---------|
| `autodev-proposal` | Proposed improvement, awaiting approval |
| `autodev-approved` | Approved, will be implemented in next run |
| `autodev-draft` | Draft PR created, awaiting review |

### Focus Areas

**Protocols:** OpenID4VCI, OpenID4VP, SIOPv2, ISO 18013-5, OID4IDA

**Credential Formats:** SD-JWT, mdoc/mDL, W3C VC, JWT-VC

### Monitored Standards

- [EU Age Verification](https://ageverification.dev/)
- [EUDI Wallet ARF](https://eudi.dev/)
- [OpenID4VCI/VP Specs](https://openid.net/)

### Configuration

AutoDev is configured via [autodev-agent](https://github.com/privacybydesign/autodev-agent).

---
*This issue is automatically updated by AutoDev Agent*
"""

REPOS = [
    "privacybydesign/irmago",
    "privacybydesign/irmamobile",
]

LABELS = [
    {"name": "autodev-proposal", "color": "7057ff", "description": "Proposed by AutoDev Agent"},
    {"name": "autodev-approved", "color": "0e8a16", "description": "Approved for implementation"},
    {"name": "autodev-draft", "color": "fbca04", "description": "Draft PR by AutoDev Agent"},
    {"name": "autodev-tracking", "color": "1d76db", "description": "AutoDev tracking issue"},
]


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: Set GH_TOKEN or GITHUB_TOKEN environment variable")
        sys.exit(1)

    gh = Github(token)

    for repo_name in REPOS:
        print(f"\nSetting up {repo_name}...")
        repo = gh.get_repo(repo_name)

        # Create labels
        existing_labels = {label.name for label in repo.get_labels()}
        for label in LABELS:
            if label["name"] not in existing_labels:
                try:
                    repo.create_label(**label)
                    print(f"  Created label: {label['name']}")
                except Exception as e:
                    print(f"  Failed to create label {label['name']}: {e}")

        # Check for existing tracking issue
        existing = list(repo.get_issues(state="open", labels=["autodev-tracking"]))
        if existing:
            print(f"  Tracking issue already exists: #{existing[0].number}")
            continue

        # Create tracking issue
        issue = repo.create_issue(
            title=TRACKING_ISSUE_TITLE,
            body=TRACKING_ISSUE_BODY,
            labels=["autodev-tracking"],
        )
        print(f"  Created tracking issue: #{issue.number}")

    print("\nSetup complete!")


if __name__ == "__main__":
    main()
