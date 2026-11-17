# HYDROSIGHT — GitHub Actions and DVC automation

## Scope

The existing **HYDROSIGHT CI** workflow checks Python syntax, automated tests and EDA notebooks on pushes and pull requests. The separate **HYDROSIGHT DVC Pipeline** workflow operates on the existing real Calgary source snapshots: it retrieves DVC data, reproduces the preprocessed datasets and 500 m sector break history, verifies their consistency and, when manually authorized, publishes versioned artifacts for review.

**This is not a new-observations ingestion workflow.** The current `dvc.yaml` references specific October 2026 snapshots. A weekly check verifies reproducibility and remote availability; it does not check Calgary's APIs for newer records, update fixed input paths, monitor model drift or retrain an ML model. Those features require additional implementation with verified data contracts.

## One-time Google Drive configuration

1. Enable the Google Drive API in a Google Cloud project and create a dedicated service account with a JSON key. Never place the key in source code.
2. Grant the service account access to the existing DVC Google Drive folder, using the address in `client_email`. Reading requires viewer permission; publishing requires sufficient write permission. Check Drive storage and service-account policy restrictions before attempting publication.
3. In the repository, open **Settings → Secrets and variables → Actions → Secrets**. Create `HYDROSIGHT_GDRIVE_SERVICE_ACCOUNT_JSON` and paste the full JSON **only in the secret field**. Never paste secrets into issues, chat messages, workflow files or build logs.
4. Open **Actions → HYDROSIGHT DVC Pipeline → Run workflow**, select **validate**, and inspect the job logs.
5. Only after this first validation succeeds, set the GitHub repository variable `HYDROSIGHT_DVC_ENABLED` to `true` in **Settings → Secrets and variables → Actions → Variables**. This enables read-only checks after relevant `main` pushes and every Monday at 10:29 UTC.
6. For deliberate publication, run **publish** manually on `main`. It validates the pipeline, calls `dvc push`, and opens a review PR if DVC metadata changed. It never merges automatically. The repository may require enabling **Settings → Actions → General → Allow GitHub Actions to create and approve pull requests**.

A GitHub runner does not inherit OAuth tokens stored on a developer's Mac. The workflow uses the dedicated secret via `GDRIVE_CREDENTIALS_DATA` and configures `gdrive_use_service_account` only in ignored local DVC settings.

## Behavior

| Trigger | Behavior |
| --- | --- |
| Pull request | Existing CI only; no Google Drive credentials |
| Relevant push to `main` | Read-only DVC validation when `HYDROSIGHT_DVC_ENABLED=true` |
| Weekly schedule | Read-only DVC validation when enabled |
| Manual `validate` | DVC pull, reproduce, test, verify history, inspect remote |
| Manual `publish` on `main` | Validate, push DVC artifacts, create PR for updated DVC metadata |

The pipeline never uses synthetic production data, auto-commits to `main`, downloads replacements for official Calgary snapshots, or retrains ML models.

The publishing workflow changes only the DVC lockfile and `data/pipeline/.gitignore` through a review PR. DVC data remain in the configured Google Drive remote. Depending on repository GitHub Actions settings, a PR opened with `GITHUB_TOKEN` may not automatically launch the CI workflow, so the reviewer must verify check results before merging.

## Local equivalent

```bash
bash scripts/verify_dvc_pipeline.sh
dvc status -c

# Only when intentionally publishing validated outputs:
dvc push
```

## References

- [DVC Google Drive remote configuration](https://dvc.org/doc/user-guide/data-management/remote-storage/google-drive)
- [GitHub Actions repository settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
