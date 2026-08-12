# ECC CI/CD Pipeline Reference

Source: adapted from ECC `deployment-patterns` skill (affaan-m/ECC).  
Use this as the canonical reference when the human asks for a CI/CD pipeline, GitHub Actions setup, or “what should run on push/PR”.

**Guided family rules still apply**
- AI shows the complete minimal pipeline.
- Human types / owns the final `.github/workflows/` files.
- AI never creates the files unless the human explicitly asks.
- Apply Ponytail: smallest pipeline that still gives real confidence.

## Standard Pipeline Stages

| Trigger              | Stages                                                                 |
|----------------------|------------------------------------------------------------------------|
| **PR opened**        | lint → typecheck → unit tests → integration tests → (optional preview) |
| **Merged to main**   | lint → typecheck → unit tests → integration tests → build → deploy     |

## Minimal GitHub Actions Example (recommended starting point)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm          # or pnpm / yarn

      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
```

### When you also need build + deploy (main only)

Add these jobs after `test`:

```yaml
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      # … build image or artifacts …

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production   # enables protection rules & secrets
    steps:
      - name: Deploy
        run: |
          # Platform-specific command (Railway, Vercel, kubectl, etc.)
          echo "Deploying ${{ github.sha }}"
```

## Ponytail Rules for Pipelines

1. Start with the **test job only**. Add build/deploy only when the project actually needs them.
2. Prefer the package manager and Node version already used by the project.
3. Cache aggressively (`cache: npm` / `cache-from: type=gha`).
4. Fail fast: later jobs `needs: test`.
5. Minimal permissions (`contents: read` unless you truly need more).
6. Never put secrets in the workflow file — use GitHub Environments + repository secrets.
7. Keep the YAML readable. No clever abstractions until the simple version is proven.

## What the guided family should do with this reference

When the human asks for CI/CD:

1. Load this reference.
2. Detect the project’s real package manager, test command, and language from project memory / codebase.
3. Show the **smallest complete pipeline** that matches the project (usually just the `test` job first).
4. Tell the human to create `.github/workflows/ci.yml` and type the content.
5. Offer to refine after they paste their version or after the first run fails.

This keeps the AI in the assistant seat and the human as the owner of the pipeline.
