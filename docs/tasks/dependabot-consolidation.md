# Task: Consolidate Dependabot PRs & Fix Vulnerability Alerts

## Overview

Periodically, Dependabot opens many small PRs and flags vulnerability alerts. Instead of merging each PR individually, we consolidate all dependency updates into a single branch, resolve conflicts, verify the build, and merge once.

## 1. Audit Current State

Check open Dependabot PRs and vulnerability alerts:

```bash
# List open Dependabot PRs
gh pr list --author "app/dependabot" --state open

# Count and list open vulnerability alerts
gh api repos/Blaxzter/wirksam/dependabot/alerts \
  --jq '[.[] | select(.state == "open")] | length'

gh api repos/Blaxzter/wirksam/dependabot/alerts \
  --jq '[.[] | select(.state == "open")] | sort_by(.security_advisory.severity) | .[] | "\(.security_advisory.severity) | \(.dependency.package.name) | \(.security_advisory.summary)"'
```

## 2. Update Dependencies Locally

### Frontend (npm packages)

Most alerts and PRs target the frontend. Update everything at once:

```bash
cd frontend

# Update all dependencies to latest compatible versions
pnpm update

# For major version bumps (review breaking changes first)
pnpm update --latest

# Check for remaining outdated packages
pnpm outdated
```

### Backend (Python packages)

```bash
cd backend

# Update all dependencies
uv lock --upgrade

# Or update a specific package
uv lock --upgrade-package <package-name>
```

### GitHub Actions

Update action versions in `.github/workflows/*.yml` manually based on the open Dependabot PRs. Match the versions Dependabot suggests.

### Docker base images

Update base image tags in Dockerfiles (`frontend/Dockerfile`, `backend/Dockerfile`) based on open Dependabot PRs.

## 3. Verify the Build

```bash
# Backend
just lint-backend
just test-backend

# Frontend
just lint-frontend
cd frontend && pnpm build

# E2E (optional but recommended)
just test-e2e
```

## 4. Commit with Consistent Message

Use this commit message format for all dependabot consolidation commits:

```
chore(deps): consolidate dependency updates

- Updated frontend npm packages
- Updated backend Python packages
- Updated GitHub Actions versions
- Updated Docker base images
- Resolved X Dependabot alerts

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

Adjust the bullet points to reflect what was actually updated. Keep the `chore(deps):` prefix consistent.

## 5. Push & Let PRs Auto-Close

Push to `dev` (or your working branch). Once merged to `main`, Dependabot PRs whose changes are already included will auto-close.

```bash
git push origin dev
```

After merging to `main`, verify PRs closed:

```bash
gh pr list --author "app/dependabot" --state open
```

Any remaining open PRs were not covered by the bulk update and need individual attention.

## 6. Dismiss Remaining Alerts

If any alerts persist after the update (e.g., transitive dependencies you can't control), review and dismiss with a reason:

```bash
gh api --method PATCH repos/Blaxzter/wirksam/dependabot/alerts/<alert_number> \
  -f state=dismissed -f dismissed_reason="tolerable_risk" \
  -f dismissed_comment="Transitive dep, no direct exposure"
```

## Current Snapshot (2026-04-05)

### Open PRs (14)

| PR  | Update |
| --- | ------ |
| #27 | Grouped npm update (10 packages) |
| #19 | lucide-vue-next 0.525.0 → 1.0.0 |
| #18 | Docker node 24-alpine → 25-alpine |
| #17 | Docker playwright v1.49.0 → v1.58.2 |
| #16 | @vue/eslint-config-typescript 14.6.0 → 14.7.0 |
| #15 | vite-plugin-vue-devtools 7.7.7 → 8.1.1 |
| #14 | vite-svg-loader 5.1.0 → 5.1.1 |
| #13 | actions/labeler 5.0.0 → 6.0.1 |
| #12 | @trivago/prettier-plugin-sort-imports 5.2.2 → 6.0.2 |
| #11 | Docker python 3.10 → 3.14 |
| #10 | actions/download-artifact 5.0.0 → 8.0.1 |
| #9  | icalendar >=6.0.0,<7.0.0 → >=6.0.0,<8.0.0 |
| #8  | actions/upload-artifact 4.6.2 → 7.0.0 |
| #7  | actions/setup-node 4.4.0 → 6.3.0 |
| #6  | astral-sh/setup-uv hash update |

### Vulnerability Alerts (22 open, all npm)

| Severity | Package | Issue |
| -------- | ------- | ----- |
| critical | handlebars | JS Injection via AST Type Confusion |
| high | defu | Prototype pollution via `__proto__` |
| high | lodash, lodash-es | Code Injection via `_.template` |
| high | handlebars (×3) | JS Injection variants |
| high | picomatch | ReDoS via extglob quantifiers |
| high | flatted | Prototype Pollution via parse() |
| high | tar (×2) | Symlink/Hardlink Path Traversal |
| high | svgo | DoS via entity expansion |
| high | minimatch (×2) | ReDoS via GLOBSTAR segments |
| high | rollup | Arbitrary File Write via Path Traversal |
| medium | lodash, lodash-es | Prototype Pollution via array path |
| medium | handlebars (×2) | Prototype Pollution / Access Control Gap |
| medium | picomatch (×2) | Method Injection in POSIX classes |
| low | handlebars | Property Access Validation Bypass |
