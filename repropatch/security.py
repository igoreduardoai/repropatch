"""Filesystem and artifact boundaries. These are not an OS sandbox."""
import hashlib
from pathlib import Path

class BoundaryError(ValueError): pass

def safe_path(root: Path, relative: str, must_exist=False) -> Path:
    if not relative or "\\" in relative or "\x00" in relative:
        raise BoundaryError("Invalid relative path")
    value=Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise BoundaryError("Absolute paths and traversal are forbidden")
    root=root.resolve()
    # Reject symlinks even when they currently resolve back inside the root.
    cur=root
    for part in value.parts:
        cur=cur/part
        if cur.is_symlink(): raise BoundaryError("Symlinks are forbidden")
    path=(root/value).resolve()
    if not path.is_relative_to(root): raise BoundaryError("Path escapes workspace")
    if must_exist and not path.is_file(): raise BoundaryError("File does not exist")
    return path

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def freeze_test(path: Path, evidence_dir: Path) -> dict:
    body=path.read_bytes()
    evidence_dir.mkdir(parents=True,exist_ok=True)
    destination=evidence_dir/"reproduction.frozen.mjs"
    if destination.exists(): raise BoundaryError("Frozen test already exists")
    destination.write_bytes(body)
    return {"sha256":sha256(body),"bytes":len(body),"path":str(destination)}

def freeze_bytes(body: bytes, evidence_dir: Path, name: str) -> dict:
    """Write an immutable copy OUTSIDE any agent workspace and record its hash."""
    if "/" in name or name.startswith("."): raise BoundaryError("Invalid evidence name")
    evidence_dir.mkdir(parents=True,exist_ok=True)
    destination=evidence_dir/name
    if destination.exists(): raise BoundaryError("Frozen test already exists")
    destination.write_bytes(body); destination.chmod(0o444)
    return {"sha256":sha256(body),"bytes":len(body),"path":str(destination)}

def check_frozen(path: Path, expected_sha: str):
    if sha256(path.read_bytes()) != expected_sha:
        raise BoundaryError("Frozen reproduction test was modified")
