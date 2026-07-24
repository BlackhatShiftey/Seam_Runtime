from __future__ import annotations

import argparse
import io
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

FORBIDDEN_PATH_PARTS = {
    "seam_runtime",
    "benchmarks",
    "holdouts",
    "mirl",
    "hs1",
    "holographic",
    "surface_adapters",
}
FORBIDDEN_CODE_MARKERS = (
    b"seam_runtime",
    b"MIRLRecord",
    b"compile_nl",
    b"pack_ir",
    b"holographic",
    b"surface_adapters",
)


def verify(path: Path) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        _verify_wheel(members)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            members = {
                member.name: archive.extractfile(member).read()
                for member in archive.getmembers()
                if member.isfile() and archive.extractfile(member) is not None
            }
        _verify_sdist(members)
    else:
        raise ValueError(f"unsupported distribution: {path}")


def _verify_wheel(members: dict[str, bytes]) -> None:
    for name, body in members.items():
        path = PurePosixPath(name)
        top = path.parts[0]
        if top != "seam_client" and not top.startswith("seam_client-"):
            raise ValueError(f"wheel contains unexpected top-level path: {name}")
        _verify_member(name, body)
    metadata = _single_metadata(members)
    _verify_metadata(metadata)


def _verify_sdist(members: dict[str, bytes]) -> None:
    roots = {PurePosixPath(name).parts[0] for name in members}
    if len(roots) != 1:
        raise ValueError(f"sdist must have one root directory, found: {sorted(roots)}")
    root = next(iter(roots))
    if not root.startswith("seam_client-"):
        raise ValueError(f"unexpected sdist root: {root}")
    for name, body in members.items():
        path = PurePosixPath(name)
        relative = PurePosixPath(*path.parts[1:])
        if relative.parts and relative.parts[0] not in {
            "src",
            "tests",
            "LICENSE",
            "PKG-INFO",
            "README.md",
            "pyproject.toml",
            "setup.cfg",
        }:
            raise ValueError(f"sdist contains unexpected path: {name}")
        _verify_member(str(relative), body)
    pkg_info = members.get(f"{root}/PKG-INFO")
    if pkg_info is None:
        raise ValueError("sdist is missing PKG-INFO")
    _verify_metadata(pkg_info)


def _verify_member(name: str, body: bytes) -> None:
    lowered_parts = {part.lower() for part in PurePosixPath(name).parts}
    overlap = lowered_parts & FORBIDDEN_PATH_PARTS
    if overlap:
        raise ValueError(
            f"distribution contains reserved path component {sorted(overlap)}: {name}"
        )
    if name.endswith(".py") and "seam_client" in PurePosixPath(name).parts:
        for marker in FORBIDDEN_CODE_MARKERS:
            if marker.lower() in body.lower():
                raise ValueError(
                    f"public SDK code contains private-runtime marker "
                    f"{marker.decode()!r}: {name}"
                )


def _single_metadata(members: dict[str, bytes]) -> bytes:
    matches = [body for name, body in members.items() if name.endswith(".dist-info/METADATA")]
    if len(matches) != 1:
        raise ValueError(f"wheel must contain exactly one METADATA file, found {len(matches)}")
    return matches[0]


def _verify_metadata(raw: bytes) -> None:
    message = BytesParser().parse(io.BytesIO(raw), headersonly=True)
    if message.get("Name") != "seam-client":
        raise ValueError(f"unexpected package name: {message.get('Name')!r}")
    if message.get("License-Expression") != "Apache-2.0":
        raise ValueError(
            f"unexpected license expression: {message.get('License-Expression')!r}"
        )
    if message.get("Version") != "0.1.0":
        raise ValueError(f"unexpected package version: {message.get('Version')!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless a distribution contains only the public SEAM SDK."
    )
    parser.add_argument("distributions", nargs="+", type=Path)
    args = parser.parse_args()
    for distribution in args.distributions:
        verify(distribution)
        print(f"public SDK boundary passed: {distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
