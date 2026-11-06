# Debian 12 Posit-style R — v4/v4.1

**Unofficial community build, not an official Posit binary.** Uses the upstream
[`rstudio/r-builds`](https://github.com/rstudio/r-builds) compilation script and
restores its retired Debian 12 builder. The Debian 12 Dockerfile and nFPM
packaging script are **unchanged from the previously tested v3**.

These workflows are designed for a repository hosted on **GitHub.com** with Actions
enabled. The original v3 build of R 4.6.2 passed GitHub Actions and also passed
Debian 12 real-machine smoke tests, including MKL linkage through Debian alternatives.
**v4/v4.1 has been syntax-checked but has not yet completed a real GitHub Actions run.**

## Crucial safety rule: no automatic compilation or publication

| Workflow | Trigger | What it does |
|---|---|---|
| `Check upstream R release (no build)` | Daily / manual | Reads CRAN stable-version list, opens one Issue for a newer version; **never builds** |
| `Build Posit-style R for Debian 12` | **Manual Run workflow only** | Builds and tests the package, then saves a 30-day Actions artifact; **never creates a release** |
| `Publish verified R artifact (manual only)` | **Manual Run workflow only** | Verifies and republishes the exact artifact from a successful build run; **never recompiles R** |

The build and publish workflows have no `push`, `schedule`, `workflow_run`, or
`repository_dispatch` triggers.

## Files

```text
.github/
  r-version-baseline.txt
  scripts/
    latest_r.py             # unchanged v3 stable-release detector
    write_manifest.py       # v4 build provenance
    verify_artifact.py      # v4.1 promotion checks
  workflows/
    check-upstream-r.yml    # unchanged v3 version check
    build-r-debian12.yml    # v4, manual only
    publish-release.yml     # v4.1, manual only

debian12/
  Dockerfile.debian-12      # unchanged from working v3
  package.debian-12         # unchanged from working v3
README.md
```

### Upgrade an existing v3 repository

Copy **all files** from the ZIP into your existing repository, preserving the
folders. The old `publish_release` parameter is **removed** from the build
workflow on purpose. Do not keep the old in-build `softprops/action-gh-release`
step. You may keep the existing default branch and existing GitHub Issues.

## Step A — Manually build

Go to **Actions → Build Posit-style R for Debian 12 → Run workflow** and set:

- `r_version`: `latest` or an exact release such as `4.6.2`.
- `posit_ref`: a **full 40-character upstream commit SHA** for reproducibility,
  or `main` for an exploratory first build. After checkout, the workflow **freezes
  the resolved exact commit** for that run; it writes the SHA to the manifest.
- `debian_base_ref`: `debian:bookworm`, or an exact previously recorded
  `debian@sha256:...` digest. The workflow resolves the tag to a digest **before
  building**, then builds using that frozen digest.

**How to repeat an earlier build as closely as possible:** get its
`BUILD-MANIFEST.json`, copy the `rebuild_inputs` values into the next manual
build. Do **not** use `main`/`latest` if you want repeatable inputs.

The workflow keeps the known-good Posit build script and Debian 12 package
configuration. The smoke test checks `R --version`, Cairo, a BLAS matrix
operation, generic `-lblas/-llapack` flags, Debian OpenBLAS alternatives, and
**installs Rcpp from source and evaluates compiled C++ code** in an isolated
container. It does not touch any single-cell analysis library on a real server.

Successful output: an Artifact named like `r-4.6.2-debian12-amd64`, containing

```text
debian-12/r-4.6.2_1_amd64.deb
r/debian-12/R-4.6.2-debian-12.tar.gz
BUILD-MANIFEST.json
BUILD-ENVIRONMENT.txt
BUILD-INFO.txt
TEST-REPORT.txt
SHA256SUMS
posit-upstream-commit.txt
debian-base-image.txt
r-source-reference-sha256.txt
rcpp-smoke-version.txt
local-build-files-sha256.txt
builder-image-id.txt
```

`BUILD-MANIFEST.json` tracks R version, upstream SHA, Debian base digest,
R source reference SHA256, local builder scripts' hashes, toolchain/dependency
inventory, binary SHA256 hashes, GitHub workflow commit/run, tested Rcpp version,
and full re-run inputs. `SHA256SUMS` covers all files in the artifact.

### Important reproducibility limitation

This is **traceable and repeatable-input building**, not guaranteed bit-for-bit
reproducibility. The original Posit `build.sh` **downloads R source independently**;
CI records the SHA256 of a CRAN reference source tarball but does **not attest
that the separately downloaded bytes are identical**. In addition, `apt` packages
and the newest CRAN Rcpp source test can change over time. The build environment
records exact `dpkg-query` versions and the Rcpp version that passed. For
fully hermetic builds, a future revision must pin apt repositories, Rcpp source,
and verify the in-builder R tarball against the reference SHA; those changes are
intentionally not made to the already working compilation pipeline here.

## Step B — Manually promote the exact successful Artifact to a Release

1. Open the **successful Build Posit-style R for Debian 12** run. Copy the numeric
   **run ID** from its URL, e.g. `https://github.com/OWNER/REPO/actions/runs/123456789`.
2. Confirm you are satisfied with the build and smoke tests. You can also test
   the Artifact on an isolated Debian 12 machine before promotion.
3. Go to **Actions → Publish verified R artifact (manual only) → Run workflow**.
4. Enter `build_run_id=123456789`, keep `draft_release=true` initially.
5. When the publish workflow succeeds, review the draft under **Releases** and
   click **Publish release** when ready. Alternatively, manually run with
   `draft_release=false` to publish immediately.

The promotion workflow checks the GitHub API to establish that the source run:
- belongs to this repository and the actual build workflow;
- was **manually dispatched** and finished with conclusion `success`;
- has exactly one non-expired artifact with the expected R-build naming format.

It downloads **only that Artifact**, checks `SHA256SUMS`, validates manifest
run ID/attempt/source-commit against the API, validates `.deb`/tar.gz hashes,
and requires an Rcpp PASS report. It **does not run Docker, compile R, or
repackage any payload**. The Release tag includes the build run ID, e.g.
`r-4.6.2-debian12-run123456789`, avoiding collisions between builds.

The Release tag targets the source repository commit of the original build, not
the commit of the separate publishing workflow.

**Artifact retention:** GitHub Actions artifacts expire (here after 30 days).
If you do not promote within that period, run a **new manual build**. Releases
persist independently of Actions artifact retention, subject to repository
settings and GitHub's policies.

## Installing on Debian 12

Only install on **Debian 12 amd64**, not Ubuntu 22.04. Before installation,
check `SHA256SUMS` from the downloaded Artifact:

```bash
sha256sum -c SHA256SUMS
sudo apt install ./debian-12/r-4.6.2_1_amd64.deb
/opt/R/4.6.2/bin/Rscript --vanilla -e 'sessionInfo()'
/opt/R/4.6.2/bin/R CMD config BLAS_LIBS
/opt/R/4.6.2/bin/R CMD config LAPACK_LIBS
```

`-lblas` / `-llapack` uses Debian alternatives, allowing compatible system
OpenBLAS or Intel oneMKL configurations. CI validates OpenBLAS, **not MKL**.
R 4.6 may require selective recompilation of old R 4.5 binary packages; do not
assume an existing Seurat library is automatically compatible.

## Token permissions and security

- Build: only `contents: read`.
- Publisher: `actions: read` and `contents: write` to create the Release.
- R-version watcher: `contents: read`, `issues: write`, as in v3.
- Uses `GITHUB_TOKEN`, no PAT or secrets required.
- `actions/checkout` and `actions/upload-artifact` use full immutable action
  commits in v4; other v3 components remain unchanged.
- `gh` and `jq` are available on GitHub-hosted Ubuntu runners.

Recommended repository settings: Issues enabled for the watcher; protect the
default branch and require review for changes to workflows and build scripts.

## References

- Upstream R build tooling: https://github.com/rstudio/r-builds
- R source: https://cran.r-project.org/src/base/
- GitHub Actions artifacts: https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts
- GitHub CLI release create: https://cli.github.com/manual/gh_release_create

