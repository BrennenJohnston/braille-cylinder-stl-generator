# Release Process

## Versioning

This project uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **Major** — breaking changes (API structure, removed features)
- **Minor** — new features, non-breaking enhancements
- **Patch** — bug fixes, dependency updates, docs

Version is tracked in `package.json`, `package-lock.json` (`npm version X.Y.Z --no-git-tag-version` updates both), `pyproject.toml` and the version badge at the top of `README.md` (its number and its release link). Keep them in sync.

## Before releasing

### Run tests

```bash
pytest tests/ -v
ruff check .
ruff format --check .
npx vitest run
npx playwright test
```

Playwright runs the browser tests in Chromium, Firefox and WebKit. CI runs all of these on every push to `develop` or `main` and on pull requests to them (jobs backend-tests, frontend-tests, e2e-tests and accessibility-tests).

### Run Lighthouse

```bash
FLASK_ENV=development python backend.py &
lighthouse http://localhost:5001 --only-categories=accessibility
```

Start the server in development mode, as CI does: in production mode it tells the browser to fetch the page's files over HTTPS, which a plain local server cannot answer. CI's accessibility-tests job runs Lighthouse CI (`lhci autorun`, settings in `lighthouserc.json`).

Target: 100/100 accessibility score.

### Manual smoke test

- [ ] App loads in browser
- [ ] Choose an Embosser setup (version, card sides, gears)
- [ ] Type text; Generate STL builds both cylinders
- [ ] The Braille (Unicode) box fills with the braille that was embossed
- [ ] The 3D preview shows both cylinders
- [ ] Download STL saves one `Cylinder_Pair_…stl` file
- [ ] Repeat once on a phone

### Security check

- [ ] No secrets in committed code
- [ ] `pip-audit -r requirements.txt -r requirements-dev.txt` (run from a scratch virtual environment; pip-audit is not one of the project's dependencies) and `npm audit` report no known vulnerabilities

## Release steps

This project never commits to `main` directly: a release reaches `main` through a pull request from `develop`.

1. On `develop`, update the version in every place listed under Versioning
2. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new `## [X.Y.Z] - YYYY-MM-DD` section, following [Keep a Changelog](https://keepachangelog.com/) format
3. Commit and push to `develop`, and wait for CI to pass:

```bash
git add package.json package-lock.json pyproject.toml README.md CHANGELOG.md
git commit -m "Release vX.Y.Z"
git push origin develop
```

4. Open a pull request from `develop` to `main`; the maintainer reviews and merges it
5. Tag the merge commit on `main` and push the tag:

```bash
git fetch origin
git tag -a vX.Y.Z <merge-commit> -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

6. Create a GitHub Release from the tag, using the changelog section as the description
7. Vercel deploys `main` automatically after the merge — verify the production site works
8. Bring `develop` level with `main`:

```bash
git checkout develop
git merge --ff-only origin/main
git push origin develop
```

## Hotfixes

For critical bugs in production:

1. Branch from the latest tag: `git checkout -b hotfix/issue-123 vX.Y.Z`
2. Fix with minimal changes
3. Run tests, bump patch version, update changelog
4. Open a pull request into `main`; after the maintainer merges it, tag the merge commit and create the GitHub Release as in release steps 5 and 6 (Vercel deploys `main`)
5. Merge `main` back into `develop` so the fix is not lost: `git checkout develop && git merge origin/main`

## Rollback

In the Vercel dashboard, find the previous deployment and click "Promote to Production." Don't force-push or delete tags.

## Release history

See [CHANGELOG.md](../CHANGELOG.md).
