# Release process

QGIS2Mapbender is released in two separate stages. The package must be
accepted and published by the official QGIS plugin repository before a
GitHub release is created.

## 1. Prepare the version

1. Update `qgis2mapbender/metadata.txt` with the new plugin version.
2. Add the corresponding entry to `CHANGELOG.md`.
3. Merge the changes into `main`.
4. Run the **Test QGIS plugin package** workflow from the GitHub Actions tab.
   This workflow:
   - runs Bandit over the plugin source;
   - scans the source with detect-secrets;
   - runs the active QGIS Flake8 rules as advisory checks;
   - creates the plugin ZIP;
   - checks the ZIP contents, metadata version, and generated Python files.
5. Inspect the generated package artifact and confirm that its metadata
   contains the expected version.

Do not create a Git tag or GitHub release at this stage.

## 2. Submit the package to QGIS.org

Run the **Submit QGIS plugin version** workflow manually from the GitHub
Actions tab:

1. Open **Actions** and select **Submit QGIS plugin version**.
2. Click **Run workflow**.
3. Select `main` in the branch selector.
4. Enter the following workflow inputs:
   - `version`: the exact value in `qgis2mapbender/metadata.txt`, without the
     `v` prefix, for example `1.2.2`.

The workflow always checks out the `main` commit associated with the workflow
run. It records that commit in the workflow summary and in the submitted
artifact.

This workflow repeats Bandit, detect-secrets, and Flake8, validates the
generated ZIP, and uploads the package to `plugins.qgis.org` using the
`OSGEO_USER` and `OSGEO_PASSWORD` secrets. It does not create a GitHub tag or
release.

The checks are repeated here because this workflow is an independent
publication entry point. A previous package workflow run is not treated as a
prerequisite for uploading a package.

Wait until QGIS.org has approved and published the version. Verify that the
version is visible and downloadable from the official plugin repository.

## 3. Create the GitHub release

Only after QGIS.org has published the version, create the tag on the exact
commit recorded by the QGIS submission workflow. This is important if `main`
has advanced while QGIS was reviewing the package. The tag itself is the
`ref` used by the GitHub release workflow; no additional GitHub `ref` input is
needed.

```bash
SUBMITTED_COMMIT="a1b2c3d4e5f6789012345678901234567890abcd"
git tag -a v1.2.2 "${SUBMITTED_COMMIT}" -m "Release v1.2.2"
git push origin v1.2.2
```

Replace the example SHA with the value shown as **Submitted commit** in the
QGIS submission workflow summary, or with the value from the
`qgis-submission-commit.txt` file in its artifact. Do not type the angle
brackets from a placeholder literally.

Pushing the tag starts the **Create GitHub release after QGIS approval**
workflow. It:

1. reruns Bandit, detect-secrets, and Flake8;
2. finds the successful QGIS submission for the same commit;
3. retrieves the package produced for that submission;
4. validates its metadata and contents;
5. creates the GitHub release with that same ZIP asset.

If no successful QGIS submission exists for the tagged commit, the workflow
fails and does not create a GitHub release.

## Security and quality checks

The workflows run the shared `.github/scripts/check-qgis-quality.sh` check:

- **Bandit** scans the complete plugin source and fails the workflow when it
  finds a security issue.
- **detect-secrets** scans the plugin source for credentials, tokens, private
  keys, and high-entropy secret strings. `metadata.txt` and an optional
  `.secrets.baseline` are excluded because QGIS handles those files separately.
  Any detected secret fails the workflow.
- **Flake8** runs the active QGIS rule set from `.github/qgis-quality.env`
  with a maximum line length of 120. Its findings are advisory in this
  repository, so they are reported but do not fail the workflow.

The QGIS.org rule list is configurable and may change. The rule list in
`.github/qgis-quality.env` records the active set known when this workflow was
updated; review it against the live
[QGIS security rules reference](https://plugins.qgis.org/docs/security-scanning/rules)
when the portal changes its configuration.

## If QGIS.org rejects the package

Do not create or reuse a GitHub tag or release for the rejected version.
Correct the issue, update the plugin version and changelog, merge the new
commit into `main`, and repeat the process with the new version.

## Secrets used by the workflows

The required repository secrets are already configured. This section explains
what each secret is used for:

- `OSGEO_USER`: account used to submit packages to QGIS.org;
- `OSGEO_PASSWORD`: password for that account;
- `GITHUB_TOKEN`: provided automatically by GitHub Actions for the GitHub
  release workflow.
