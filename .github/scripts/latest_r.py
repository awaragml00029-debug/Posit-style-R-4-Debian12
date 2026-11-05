#!/usr/bin/env python3
"""Find the newest official, stable GNU R source release on CRAN.

Reads CRAN's published release tarball index; does not consult pre-release,
patched, or development snapshots. Python stdlib only.
"""

from __future__ import annotations

import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

MIRRORS = (
    "https://cran.r-project.org",
    "https://cloud.r-project.org",
    "https://stat.ethz.ch/CRAN",
)


def fetch_html(relative_path: str) -> str:
    failures = []
    for mirror in MIRRORS:
        url = f"{mirror}/{relative_path.lstrip('/')}"
        try:
            request = Request(url, headers={"User-Agent": "debian12-r-release-check/1.0"})
            with urlopen(request, timeout=25) as response:
                data = response.read(2_000_000)
            return data.decode("utf-8", errors="replace")
        except (OSError, URLError, UnicodeError) as err:
            failures.append(f"{url}: {err}")
    raise RuntimeError("Unable to read CRAN releases from any mirror:\n" + "\n".join(failures))


def latest_release() -> str:
    # Pick the newest major series listed in src/base/, so a future R 5.x
    # does not require manually modifying the watcher.
    index = fetch_html("src/base/")
    majors = {int(n) for n in re.findall(r'R-(\d+)/', index)}
    if not majors:
        raise RuntimeError("No R major-series directories found in CRAN src/base index")

    major = max(majors)
    releases_index = fetch_html(f"src/base/R-{major}/")
    # .tar.gz is an official stable source tarball; prerelease and patched
    # builds are published in different directories.
    versions = {
        (int(maj), int(minor), int(patch))
        for maj, minor, patch in re.findall(
            r'R-(\d+)\.(\d+)\.(\d+)\.tar\.gz', releases_index
        )
        if int(maj) == major
    }
    if not versions:
        raise RuntimeError(f"No stable release tarballs found in CRAN R-{major}/")
    return ".".join(map(str, max(versions)))


if __name__ == "__main__":
    try:
        print(latest_release())
    except Exception as err:
        print(f"CRAN version detection failed: {err}", file=sys.stderr)
        raise SystemExit(1)
