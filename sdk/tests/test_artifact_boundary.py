from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from tools.verify_artifact_boundary import verify

METADATA = b"""Metadata-Version: 2.4
Name: seam-client
Version: 0.1.0
License-Expression: Apache-2.0
"""


def test_wheel_boundary_accepts_public_sdk(tmp_path: Path) -> None:
    wheel = tmp_path / "seam_client-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("seam_client/client.py", "import httpx\n")
        archive.writestr("seam_client-0.1.0.dist-info/METADATA", METADATA)
    verify(wheel)


def test_wheel_boundary_rejects_private_runtime_code(tmp_path: Path) -> None:
    wheel = tmp_path / "seam_client-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("seam_client/client.py", "from seam_runtime import runtime\n")
        archive.writestr("seam_client-0.1.0.dist-info/METADATA", METADATA)
    with pytest.raises(ValueError, match="private-runtime marker"):
        verify(wheel)


def test_sdist_boundary_rejects_reserved_tree(tmp_path: Path) -> None:
    sdist = tmp_path / "seam_client-0.1.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, body in {
            "seam_client-0.1.0/PKG-INFO": METADATA,
            "seam_client-0.1.0/src/seam_client/client.py": b"import httpx\n",
            "seam_client-0.1.0/seam_runtime/storage.py": b"private = True\n",
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
    with pytest.raises(ValueError, match="unexpected path"):
        verify(sdist)
