import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH, override=True)

MTS_DIALOG_URL = (
    "https://raw.githubusercontent.com/abachaa/MTS-Dialog/main/"
    "Main-Dataset/MTS-Dialog-ValidationSet.csv"
)


@lru_cache
def get_hf_model_id() -> str:
    return os.getenv("HF_MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")


@lru_cache
def get_hf_token() -> str:
    token = (
        os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HF_TOKEN")
        or ""
    ).strip()
    if not token or token == "hf_your_token_here":
        env_hint = f"Expected token in {_ENV_PATH}"
        if not _ENV_PATH.exists():
            env_hint = f".env file not found at {_ENV_PATH}"
        raise ValueError(
            "HUGGINGFACEHUB_API_TOKEN is not set. "
            f"Save your Hugging Face token in .env and restart the API. {env_hint}"
        )
    return token
