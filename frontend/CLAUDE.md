# Frontend CI gates

These are the checks that fail *after* the obvious ones pass, so they are easy
to miss locally and cost a full CI round trip each. Run them before pushing.

## New files under src/lib, src/composables, src/stores need tests

`vitest.config.ts` sets `perFile: true` coverage thresholds — 90% for
`src/lib/**` and friends. A brand-new helper with no spec sits at 0% and fails
the build with:

```
ERROR: Coverage for lines (0%) does not meet "src/lib/**" threshold (90%) for src/lib/<file>.ts
```

Existing untested files are carved out by name in the config's `!(…)`
exceptions; new ones are not, and should not be added there without a reason.

```bash
pnpm test:unit:coverage   # this is the gate, not `pnpm test:unit`
```

## Generated files are committed and diffed

Three artefacts are produced by scripts and verified in CI. Regenerate and
commit them whenever their inputs change:

| File | Regenerate with | Changes when |
|------|-----------------|--------------|
| `e2e/COVERAGE.md` | `pnpm generate-e2e-coverage` | any E2E test is added, renamed or removed |
| `src/client/**` | `just generate-client` (repo root) | the backend OpenAPI schema changes |
| `src/changelog/generated/` | `pnpm generate-changelog` | a changelog entry is added (gitignored, but needed for type-check) |

`src/client/**` is the one that bites: **regenerate it after the backend change
is final**, not partway through. Deleting a router later leaves stale types
behind, and the `Generate Client` workflow will notice and push a correction
commit onto your branch — which you then have to rebase onto.

## The whole job, locally

```bash
pnpm exec eslint .                             # not `pnpm lint` — that auto-fixes
node ../scripts/pre-commit/check_locale_parity.js
pnpm generate-e2e-coverage && git diff --exit-code e2e/COVERAGE.md
pnpm generate-changelog
pnpm type-check
pnpm type-check:unit                           # separate config; specs are type-checked too
pnpm test:unit:coverage
pnpm build-only
```

ESLint reports 4 pre-existing warnings (`playwright/no-conditional-in-test`).
CI does not pass `--max-warnings`, so warnings are tolerated; errors are not.
