from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from backend.config import get_hf_model_id, get_hf_token


@lru_cache
def get_llm() -> BaseChatModel:
    endpoint = HuggingFaceEndpoint(
        repo_id=get_hf_model_id(),
        task="text-generation",
        max_new_tokens=1024,
        do_sample=False,
        repetition_penalty=1.03,
        huggingfacehub_api_token=get_hf_token(),
    )
    return ChatHuggingFace(llm=endpoint)
