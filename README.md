# Debian 12 native R, Posit-style GitHub Actions (v2)

**Unofficial/community build, not a Posit release.**

This project restores native **Debian 12 Bookworm** builds using the upstream [rstudio/r-builds](https://github.com/rstudio/r-builds) `builder/build.sh` and `patches`, and a Debian 12 build environment modeled after Posit's historical Debian 12 Dockerfile.

## Why v2?

The previous archive installed **`libopenblas-dev` in the build container**. Posit's native Ubuntu and historical Debian instructions deliberately install only `libopenblas0-pthread` and let `r-base` build dependencies bring in `libblas-dev` and `liblapack-dev`. This makes R link via **generic `-lblas` and `-llapack`**, allowing the Debian `update-alternatives` system to choose OpenBLAS or a separately installed MKL later.

This revision removes `libopenblas-dev` from the build stage, uses `apt-get build-dep r-base` like the historical Posit recipe, updates `.deb` runtime dependencies, and makes the smoke test assert generic linkage **plus** OpenBLAS runtime selection. It does NOT include MKL and does NOT touch any existing server's alternatives. The CI test runs inside a disposable Debian 12 container.

## Files

```text
.github/workflows/build-r-debian12.yml
README.md
debian12/Dockerfile.debian-12
debian12/package.debian-12
```

## Run

1. Upload these files (including hidden `.github/`) to a new GitHub repository's default branch.
2. Go to **Actions → Build Posit-style R for Debian 12 → Run workflow**.
3. Set `r_version=4.6.2`, `posit_ref=main`, `publish_release=false` for the first test.
4. Inspect the clean-container test's `sessionInfo()`, `BLAS_LIBS`, `LAPACK_LIBS`, and alternatives symlinks.
5. Download the Actions artifact containing the `.deb`, tarball, SHA256SUMS and upstream commit SHA. On success, pin `posit_ref` to the exact commit printed in the artifact.

With `publish_release=true`, the workflow can also publish a GitHub Release after its tests pass.

Expected artifact paths:

```text
debian-12/r-4.6.2_1_amd64.deb
r/debian-12/R-4.6.2-debian-12.tar.gz
SHA256SUMS
BUILD-INFO.txt
posit-upstream-commit.txt
```

## Build and test expectations

- Real `debian:bookworm` compilation, not Ubuntu or manylinux cross-compatibility.
- `/opt/R/4.6.2` installation path, no `/usr/bin/R` replacement.
- Posit's default build options (including `--enable-R-shlib`, `--enable-memory-profiling`, `--with-blas`, `--with-lapack`).
- Generic `R CMD config BLAS_LIBS` = `-lblas` and `LAPACK_LIBS` = `-llapack`.
- In a clean Bookworm test environment, both alternatives point to OpenBLAS.
- Basic R startup, Cairo capability, library existence, and matrix calculation tests.

## MKL policy

**MKL is intentionally not installed or configured.** Your existing Posit R 4.5.2 on Debian 12 already uses `update-alternatives` pointing both generic BLAS and LAPACK to Intel oneMKL 2026.2, with `MKL_INTERFACE_LAYER=GNU,LP64` and 3 threads. This v2 build is designed to keep that switching model open for a *separate later compatibility test*. It does not change any live system or claim that R 4.6.2 + MKL is fully validated.

## Optional manual install (only in a disposable Debian 12 environment at first)

After downloading the Actions artifact and extracting it, run:

```bash
sha256sum -c SHA256SUMS
sudo apt-get install ./debian-12/r-4.6.2_1_amd64.deb
/opt/R/4.6.2/bin/Rscript --vanilla -e 'sessionInfo()'
```

On a machine where the current alternatives already select MKL, the new R will also dynamically resolve those system BLAS/LAPACK links. Test MKL with R 4.6 separately before relying on it; never treat installing a new version of R as a zero-risk change to the whole server.

## Limitations and reproducibility

- This zip is statically checked but **not end-to-end compiled here** (Docker/Actions execution was unavailable). The CI build itself is the first actual compilation and installation test.
- Builds are *Posit-style*, not byte-for-byte Posit binaries. `debian:bookworm`, apt sources, upstream Posit `main`, and R sources can change. Pin upstream commit, container digest, and Debian package snapshot for stronger reproducibility.
- The result is amd64 only. Builds may be time/disk intensive. R 4.5.x and 4.6.x are the allowed version families in the workflow.
- Clean-container smoke tests do not prove that all Seurat/Bioconductor packages work. Keep your existing R 4.5.2 and all package libraries intact.

Sources: [current Posit r-builds](https://github.com/rstudio/r-builds), [historical Debian 12 builder](https://github.com/r-hub/r-builds/blob/main/builder/Dockerfile.debian-12), [Posit's Ubuntu builder](https://github.com/rstudio/r-builds/blob/main/builder/Dockerfile.ubuntu-2404), [Posit source installation docs](https://docs.posit.co/resources/install-r-source.html).
