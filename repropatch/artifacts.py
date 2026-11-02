from pathlib import Path
import uuid
from .security import safe_path, sha256
from .store import now

def save_artifact(store, data_dir: Path, run_id: str, name: str, body: bytes, content_type="text/plain"):
    root=data_dir/"artifacts"/run_id
    root.mkdir(parents=True,exist_ok=True)
    path=safe_path(root,name)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(body)
    aid=uuid.uuid4().hex
    with store.connection() as c:
        c.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?)",
            (aid,run_id,name,str(path),sha256(body),len(body),content_type,now()))
    return aid
