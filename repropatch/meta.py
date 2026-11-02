"""HTTP adapter for Meta Responses API; no paid request on import/startup.

Tested here with mocked HTTP, not with a real account. Reuse the user's passing
smoke-test request shape if the provider schema differs. No automatic retries.
"""
from pathlib import Path
import os
import uuid
import httpx
from .budget import Budget

class MetaError(RuntimeError): pass

class MetaClient:
    def __init__(self, base_url="https://api.meta.ai/v1", model="muse-wonder-1.0", api_key=None, transport=None):
        self.key=api_key or os.getenv("META_MODEL_API_KEY") or os.getenv("MODEL_API_KEY")
        if not self.key: raise MetaError("Meta API key missing from server environment")
        if base_url != "https://api.meta.ai/v1":
            raise MetaError("Only the verified Meta API host is allowed; review code before changing provider")
        self.model=model
        self.client=httpx.Client(base_url=base_url,timeout=httpx.Timeout(180,connect=15),
            headers={"Authorization":f"Bearer {self.key}"},transport=transport,follow_redirects=False)

    def close(self): self.client.close()

    def models(self):
        r=self.client.get("/models");r.raise_for_status();return r.json()

    def upload_video(self,path:Path):
        if path.suffix.lower()!=".mp4" or path.stat().st_size>50*1024*1024:
            raise MetaError("Only MP4 up to 50 MiB is allowed")
        with path.open("rb") as f:
            r=self.client.post("/files",data={"purpose":"user_data"},files={"file":(path.name,f,"video/mp4")})
        r.raise_for_status();return r.json()["id"]

    def count(self, payload: dict) -> int:
        request={k:v for k,v in payload.items() if k not in {"max_output_tokens","store"}}
        r=self.client.post("/responses/input_tokens",json=request)
        r.raise_for_status(); data=r.json()
        count=data.get("input_tokens")
        if not isinstance(count,int) or count<0:
            raise MetaError("Token-count schema not recognized; refusing unbudgeted inference")
        return count

    def respond(self,run_id:str,inputs:list,tools:list,budget:Budget,max_output_tokens=1800):
        if any(t.get("type")!="function" for t in tools):
            raise MetaError("Hosted tools are excluded from this budgeted MVP")
        payload={"model":self.model,"input":inputs,"tools":tools,
                 "reasoning":{"effort":"minimal"},"max_output_tokens":max_output_tokens,"store":False}
        # Conservative reservation: counted input + buffer, no cache assumed.
        counted=self.count(payload)
        reserved_input=max(counted+256, int(counted*1.10)+1)
        request_id=uuid.uuid4().hex
        budget.reserve(request_id,run_id,reserved_input,max_output_tokens)
        try:
            r=self.client.post("/responses",json=payload)
            r.raise_for_status()
            data=r.json()
            usage=data.get("usage",{})
            if not isinstance(usage.get("input_tokens"),int) or not isinstance(usage.get("output_tokens"),int):
                raise MetaError("Missing actual usage; stop for billing reconciliation")
            cached=usage.get("input_tokens_details",{}).get("cached_tokens",0)
            # output_tokens already includes reasoning; never add reasoning again.
            budget.settle(request_id,usage["input_tokens"],usage["output_tokens"],cached)
            return data
        except Exception:
            budget.unknown(request_id)
            raise

    @staticmethod
    def public_usage(response:dict):
        usage=response.get("usage",{})
        return {"response_id":response.get("id"),"input_tokens":usage.get("input_tokens"),
                "output_tokens":usage.get("output_tokens"),
                "cached_tokens":usage.get("input_tokens_details",{}).get("cached_tokens",0)}
