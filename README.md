# Debian 12 Posit-style R builds + upstream release watch (v3)

**Community build. Not an official Posit binary.**

This repository builds native amd64 R on **Debian 12 Bookworm** using upstream
[`rstudio/r-builds`](https://github.com/rstudio/r-builds) compilation scripts,
restoring the discontinued Debian 12 builder. The original v2 pipeline has been
validated in GitHub Actions and on a separate Debian 12 machine with R 4.6.2,
including generic BLAS/LAPACK linkage and Intel oneMKL 2026.2 numerical tests.

**v3 adds a release checker; it does not add automatic builds.**

## What is new in v3?

| Workflow | Trigger | Behavior |
|---|---|---|
| `Check upstream R release (no build)` | Every day 08:37 UTC; also `Run workflow` | Reads CRAN's official stable source release index; writes the detected version into the Actions run summary. When a newer version appears, opens exactly one GitHub Issue for that version (including after that issue has been closed). **Never compiles R.** |
| `Build Posit-style R for Debian 12` | **Manual `Run workflow` only** | Builds Debian 12 `.deb` and tarball, smoke-tests installation, uploads artifacts. Default `r_version=latest` resolves the latest official CRAN stable release **at the time you click Run workflow**. Can still build a specific version such as `4.6.2`. |

The initial version baseline is `.github/r-version-baseline.txt` = `4.6.2`.
That avoids an unnecessary notification on the first check. Do not change it
unless you intentionally want a different minimum version for notifications.

The detector reads `src/base/` and then the newest `R-MAJOR/` directory,
looking for official `R-x.y.z.tar.gz` release tarballs. It does not use
R-devel, R-patched, or CRAN pre-release directories. It uses only Python's
standard library, with CRAN and two CRAN mirror fallbacks.

## Files

```text
.github/
├── r-version-baseline.txt
├── scripts/
│   └── latest_r.py
└── workflows/
    ├── build-r-debian12.yml       # manual build only
    └── check-upstream-r.yml       # daily check, NO build
README.md
debian12/
├── Dockerfile.debian-12
└── package.debian-12
```

## Upgrade from v2 (the version you have already run)

Copy these **four** additions/changes to your repo's **default branch**:

1. **Replace** `.github/workflows/build-r-debian12.yml` with v3.
2. **Add** `.github/workflows/check-upstream-r.yml`.
3. **Add** `.github/scripts/latest_r.py`.
4. **Add** `.github/r-version-baseline.txt`.

`debian12/Dockerfile.debian-12` and `debian12/package.debian-12` are unchanged.

The check workflow needs repository **Issues enabled** and uses only the
workflow's standard `GITHUB_TOKEN`, with `issues: write` and `contents: read`.
No personal access token, webhook, email, or external service is needed.
The default branch is required for scheduled Actions workflows.

### First check

Go to **Actions → Check upstream R release (no build) → Run workflow**.
The summary should show the current official R version and explicitly say
"Build: NOT started". No issue should be created when CRAN is still at the
baseline `4.6.2`. A new official release such as R `4.6.3` will generate a
single issue (including if you later close it).

### Manual build

Go to **Actions → Build Posit-style R for Debian 12 → Run workflow** and set:

- `r_version`: `latest` (default), or a fixed release such as `4.6.2`;
- `posit_ref`: `main` or (recommended for reproducibility) a proven Posit commit SHA;
- `publish_release`: `false` (default) until the build passes your checks.

There is intentionally **no `schedule`, `workflow_run`, `push`, or `repository_dispatch`
trigger on the build workflow**. A new issue or a daily check will **never**
automatically run the 6-minute R compilation.

## Validation

`Build Posit-style R for Debian 12` verifies R startup, Cairo, BLAS matrix
multiplication, `-lblas/-llapack` generic linkage and OpenBLAS alternatives
inside a clean `debian:bookworm` container. Existing Posit R versions, MKL
configuration, and single-cell package libraries are not touched.

R 4.6.2 was additionally validated by the maintainer on a Debian 12 machine:

```text
R 4.6.2 (2026-10-29)
BLAS_LIBS = -lblas
LAPACK_LIBS = -llapack
BLAS/LAPACK = /opt/intel/oneapi/mkl/2026.2/lib/libmkl_rt.so.3
crossprod(), eigen(): PASS
```

This does not imply future R releases or all Seurat/Bioconductor packages have
been validated. New R versions remain explicitly opt-in.

## Caveats

- Scheduled GitHub Actions are run from the default branch in UTC; they may be
  delayed. GitHub may disable schedules in inactive public repositories after
  60 days; re-enable the check if necessary.
- If repository Issues are disabled, the notification step fails; enable Issues
  in **Settings → General → Features → Issues**. No build will be triggered.
- If CRAN is unavailable, version detection fails rather than guessing.
  Manual build with an explicit version such as `4.6.2` still works.
- For reproducibility, use an explicit R version and pinned `posit_ref` rather
  than `latest` and `main`.
- A future major R release is detectable by the watcher but may require
  revising upstream build scripts or Debian 12 dependencies before it compiles.
