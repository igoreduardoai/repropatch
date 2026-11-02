"""Restricted Docker command builder for the next live integration.

Container execution must be on a dedicated worker host, not a public API host.
No Docker socket or API keys enter target containers. This is not a claim that
Docker alone safely hosts arbitrary hostile multi-tenant workloads.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from .security import BoundaryError

@dataclass(frozen=True)
class SandboxLimits:
    memory: str = "2g"
    cpus: str = "1"
    timeout_seconds: int = 90
    pids: int = 128

class DockerSandbox:
    def __init__(self,image: str,limits=SandboxLimits()):
        if not re.fullmatch(r"[a-zA-Z0-9./:_@-]+",image): raise BoundaryError("Invalid image")
        self.image=image;self.limits=limits

    def command(self,workspace:Path,argv:list[str],name:str):
        if not workspace.is_dir() or workspace.is_symlink(): raise BoundaryError("Invalid workspace")
        if not argv or not all(isinstance(x,str) and "\x00" not in x for x in argv):
            raise BoundaryError("Invalid argv")
        return ["docker","run","--rm","--pull=never","--name",name,"--network=none",
                "--read-only","--cap-drop=ALL","--security-opt=no-new-privileges",
                "--user","65534:65534","--pids-limit",str(self.limits.pids),
                "--memory",self.limits.memory,"--cpus",self.limits.cpus,
                "--tmpfs","/tmp:rw,nosuid,nodev,size=128m",
                "--mount",f"type=bind,src={workspace.resolve()},dst=/workspace,readonly",
                "--workdir","/workspace",self.image,*argv]

    def run(self,workspace:Path,argv:list[str]):
        if not shutil.which("docker"): raise RuntimeError("Docker unavailable; no host fallback permitted")
        name="repropatch-"+uuid.uuid4().hex[:16]
        cmd=self.command(workspace,argv,name)
        try:
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=self.limits.timeout_seconds)
            return {"exit_code":result.returncode,"stdout":result.stdout[:32768],"stderr":result.stderr[:8192]}
        except subprocess.TimeoutExpired:
            subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=10)
            return {"exit_code":124,"stdout":"","stderr":"Sandbox timed out"}
