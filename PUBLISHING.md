# Publishing to PyPI

`pip install iso8583-fps` works once the package is on PyPI. Publishing uses
**Trusted Publishing** (OIDC) — no API tokens are stored anywhere. One-time setup,
then a single click per release.

## One-time setup (~2 minutes)

1. Create a PyPI account at https://pypi.org (and verify your email).
2. Add a **pending** Trusted Publisher (lets you claim the name on first publish):
   go to https://pypi.org/manage/account/publishing/ and add a *GitHub* publisher with:
   - **PyPI Project Name:** `iso8583-fps`
   - **Owner:** `tarvitave`
   - **Repository name:** `iso8583-fps`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. (Recommended) In the GitHub repo, create an Environment named `pypi`
   (Settings → Environments → New environment) so the publish job is gated.

## Publish a release

1. Bump `version` in `pyproject.toml` (and tag/release on GitHub if you like).
2. Run the **Publish to PyPI** workflow: repo → Actions → "Publish to PyPI" → Run workflow
   (or `gh workflow run publish.yml`). It builds the sdist + wheel and uploads via OIDC.
3. Confirm at https://pypi.org/project/iso8583-fps/ and test `pip install iso8583-fps`.
4. Add the version badge to the top of `README.md`:
   `[![PyPI](https://img.shields.io/pypi/v/iso8583-fps.svg)](https://pypi.org/project/iso8583-fps/)`

That's it — no secrets to manage, and only this repo's `publish.yml` can publish the project.
