#!/usr/bin/env python3
"""Write an auditable build manifest for the completed v4 R build."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"Missing required environment variable {name}")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=pathlib.Path, required=True)
    dist = parser.parse_args().dist.resolve()
    ver = env("R_VERSION")
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        raise ValueError("R version malformed")
    sha = (dist / "posit-upstream-commit.txt").read_text().strip()
    base = (dist / "debian-base-image.txt").read_text().strip()
    source_sha = (dist / "r-source-reference-sha256.txt").read_text().strip()
    rcpp_version = (dist / "rcpp-smoke-version.txt").read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Posit SHA invalid")
    if not re.fullmatch(r"debian@sha256:[a-f0-9]{64}", base):
        raise ValueError("Base digest invalid")
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha):
        raise ValueError("R source SHA invalid")
    if not re.fullmatch(r"\d+(?:\.\d+)+", rcpp_version):
        raise ValueError("Rcpp version invalid")

    deb = dist / "debian-12" / f"r-{ver}_1_amd64.deb"
    tarball = dist / "r" / "debian-12" / f"R-{ver}-debian-12.tar.gz"
    for path in (deb, tarball, dist / "TEST-REPORT.txt", dist / "BUILD-ENVIRONMENT.txt"):
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty build output: {path}")
    if "Rcpp source compilation and evalCpp: PASS" not in (dist / "TEST-REPORT.txt").read_text(errors="replace"):
        raise ValueError("Rcpp smoke test was not reported PASS")
    local_sources = {}
    for f in ("debian12/Dockerfile.debian-12", "debian12/package.debian-12"):
        local_sources[f] = sha256(pathlib.Path(f))

    data = {
        "schema": "community-posit-style-r/v4",
        "build_completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "target": {"os": "Debian GNU/Linux 12 (bookworm)", "arch": "amd64", "r_version": ver, "prefix": f"/opt/R/{ver}"},
        "provenance": {
            "repository": env("GITHUB_REPOSITORY"),
            "workflow_source_commit": env("GITHUB_SHA"),
            "workflow_run_id": int(env("GITHUB_RUN_ID")),
            "workflow_run_attempt": int(env("GITHUB_RUN_ATTEMPT")),
            "workflow": "build-r-debian12.yml",
            "run_url": f"https://github.com/{env('GITHUB_REPOSITORY')}/actions/runs/{env('GITHUB_RUN_ID')}",
            "posit_upstream": "rstudio/r-builds",
            "posit_ref_requested": env("POSIT_REF_REQUESTED"),
            "posit_commit": sha,
            "debian_base_ref_requested": env("DEBIAN_BASE_REF_REQUESTED"),
            "debian_base_image": base,
            "builder_image_id": (dist / "builder-image-id.txt").read_text().strip(),
            "local_build_files_sha256": local_sources,
        },
        "r_source_reference": {
            "url": env("R_SOURCE_URL"),
            "sha256": source_sha,
            "notice": "SHA256 of CRAN reference tarball independently downloaded by CI. Posit build.sh downloads the source again; exact bytes of its fetch have not been attested."
        },
        "tested": {
            "status": "passed",
            "debian12_deb_install": True,
            "r_runtime_and_cairo": True,
            "generic_blas_lapack_and_openblas": True,
            "rcpp_compiled_from_source": True,
            "rcpp_eval_cpp": True,
            "rcpp_version": rcpp_version,
        },
        "artifacts": {
            str(deb.relative_to(dist)): sha256(deb),
            str(tarball.relative_to(dist)): sha256(tarball),
        },
        "rebuild_inputs": {
            "r_version": ver,
            "posit_ref": sha,
            "debian_base_ref": base,
        },
    }
    (dist / "BUILD-MANIFEST.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    info = (
        f"R {ver} (Debian 12 amd64, unofficial Posit-style build)\n"
        f"Run: {data['provenance']['run_url']}\n"
        f"Posit commit: {sha}\nDebian base digest: {base}\n"
        f"Official CRAN source reference SHA256: {source_sha}\n"
        f"Rcpp source smoke test: PASS ({rcpp_version})\n"
        f"Source note: {data['r_source_reference']['notice']}\n"
        "For full dependency inventory and artifact hashes, see BUILD-ENVIRONMENT.txt, BUILD-MANIFEST.json, and SHA256SUMS.\n"
    )
    (dist / "BUILD-INFO.txt").write_text(info)
    print(info)


if __name__ == "__main__":
    main()
