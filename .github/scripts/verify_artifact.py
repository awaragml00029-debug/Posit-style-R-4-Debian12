#!/usr/bin/env python3
"""Fail closed if a downloaded artifact does not match its successful build run."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--dir", required=True, type=pathlib.Path)
    a.add_argument("--repo", required=True)
    a.add_argument("--run-id", required=True, type=int)
    a.add_argument("--run-attempt", required=True, type=int)
    a.add_argument("--source-commit", required=True)
    a.add_argument("--artifact-name", required=True)
    x = a.parse_args()
    root = x.dir.resolve()
    mpath = root / "BUILD-MANIFEST.json"
    d = json.loads(mpath.read_text())
    p = d["provenance"]
    t = d["target"]
    tests = d["tested"]
    ver = t["r_version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        raise ValueError("Bad R version")
    if x.artifact_name != f"r-{ver}-debian12-amd64":
        raise ValueError("Artifact name/version mismatch")
    if d["schema"] != "community-posit-style-r/v4":
        raise ValueError("Not a v4 build manifest")
    if (p["repository"], p["workflow_run_id"], p["workflow_run_attempt"], p["workflow_source_commit"]) != (
        x.repo, x.run_id, x.run_attempt, x.source_commit
    ):
        raise ValueError("Manifest does not match verified GitHub build run")
    if p["workflow"] != "build-r-debian12.yml":
        raise ValueError("Not a R build workflow")
    if (t["os"], t["arch"], t["prefix"]) != (
        "Debian GNU/Linux 12 (bookworm)", "amd64", f"/opt/R/{ver}"
    ):
        raise ValueError("Unexpected target platform")
    if not re.fullmatch(r"[a-f0-9]{40}", p["posit_commit"]):
        raise ValueError("Malformed upstream SHA")
    if (root / "posit-upstream-commit.txt").read_text().strip() != p["posit_commit"]:
        raise ValueError("Upstream SHA file differs from manifest")
    if (root / "debian-base-image.txt").read_text().strip() != p["debian_base_image"]:
        raise ValueError("Base image differs from manifest")
    if (root / "r-source-reference-sha256.txt").read_text().strip() != d["r_source_reference"]["sha256"]:
        raise ValueError("R source reference differs from manifest")
    required = (
        "status", "debian12_deb_install", "r_runtime_and_cairo",
        "generic_blas_lapack_and_openblas", "rcpp_compiled_from_source", "rcpp_eval_cpp"
    )
    if tests["status"] != "passed" or not all(tests[k] is True for k in required[1:]):
        raise ValueError("Tests not all passed")
    if (root / "rcpp-smoke-version.txt").read_text().strip() != tests["rcpp_version"]:
        raise ValueError("Rcpp test version differs from manifest")
    if "Rcpp source compilation and evalCpp: PASS" not in (root / "TEST-REPORT.txt").read_text(errors="replace"):
        raise ValueError("Rcpp execution missing from CI report")
    expected_files = set(d["artifacts"])
    mandatory = {
        f"debian-12/r-{ver}_1_amd64.deb",
        f"r/debian-12/R-{ver}-debian-12.tar.gz",
    }
    if expected_files != mandatory:
        raise ValueError("Unexpected payload file list")
    for rel, want_sha in d["artifacts"].items():
        if not re.fullmatch(r"[a-f0-9]{64}", want_sha):
            raise ValueError("Malformed payload hash")
        pth = root / rel
        if not pth.is_file() or hash_file(pth) != want_sha:
            raise ValueError(f"Payload hash mismatch: {rel}")
    required_files = mandatory | {
        "SHA256SUMS", "BUILD-INFO.txt", "BUILD-MANIFEST.json",
        "BUILD-ENVIRONMENT.txt", "TEST-REPORT.txt", "posit-upstream-commit.txt",
        "debian-base-image.txt", "r-source-reference-sha256.txt", "rcpp-smoke-version.txt",
    }
    for filename in required_files:
        if not (root / filename).is_file():
            raise ValueError(f"Missing required artifact file: {filename}")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=root, check=True)
    print(f"Verified {x.artifact_name}: success run {x.run_id}, Posit {p['posit_commit']}, Rcpp PASS")


if __name__ == "__main__":
    main()
