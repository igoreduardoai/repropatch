"""Single-operator MVP configuration. Never expose secrets through the API."""
from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    data_dir: Path
    auth_token: str
    enable_live: bool = False
    meta_base_url: str = "https://api.meta.ai/v1"
    meta_model: str = "muse-wonder-1.0"
    live_budget_usd: str = "24.00"
    run_budget_usd: str = "3.00"
    max_upload_bytes: int = 50 * 1024 * 1024
    cases_dir: Path | None = None
    acceptance_key: str = ""

    @classmethod
    def load(cls):
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            data_dir=Path(os.getenv("REPROPATCH_DATA_DIR", str(ROOT / ".data"))).resolve(),
            auth_token=os.getenv("REPROPATCH_AUTH_TOKEN", ""),
            enable_live=os.getenv("REPROPATCH_ENABLE_LIVE", "false").lower() == "true",
            meta_base_url=os.getenv("META_BASE_URL", "https://api.meta.ai/v1"),
            meta_model=os.getenv("META_MODEL", "muse-wonder-1.0"),
            live_budget_usd=os.getenv("REPROPATCH_BATCH_CAP_USD", "24.00"),
            run_budget_usd=os.getenv("REPROPATCH_RUN_CAP_USD", "3.00"),
            cases_dir=Path(os.environ["REPROPATCH_CASES_DIR"]).resolve() if os.getenv("REPROPATCH_CASES_DIR") else None,
            acceptance_key=os.getenv("REPROPATCH_ACCEPTANCE_KEY", ""),
        )

    @property
    def cases_root(self):
        return self.cases_dir or (self.data_dir / "cases")

    @property
    def db_path(self):
        return self.data_dir / "repropatch.sqlite3"
