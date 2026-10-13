"""Actual filesystem checks for the recovery archive boundary; no database mocks."""

import io
import tarfile

import pytest

from scripts.check_backup_restore import extract_dump


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        (r"\\server\share", tarfile.REGTYPE),
        ("C:/escape", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("link", tarfile.LNKTYPE),
    ],
)
def test_dump_rejects_traversal_unc_drives_and_links(tmp_path, name, kind):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as stream:
        entry = tarfile.TarInfo(name)
        entry.type, entry.linkname = kind, "../escape"
        stream.addfile(entry)
    archive.seek(0)
    with pytest.raises(ValueError, match="Unsafe"):
        extract_dump(archive, tmp_path / "backup")
    assert not (tmp_path / "escape").exists()
    assert not list((tmp_path / "backup").iterdir())


def test_dump_regular_file_is_written_inside_owned_directory(tmp_path):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as stream:
        entry = tarfile.TarInfo("./users.structure.json")
        payload = b'{"type":2}'
        entry.size = len(payload)
        stream.addfile(entry, io.BytesIO(payload))
    archive.seek(0)
    destination = tmp_path / "backup"
    extract_dump(archive, destination)
    assert (destination / "users.structure.json").read_bytes() == payload
