import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from backend.graph.state import PatientClassification

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> dict:
    """Pull the first JSON object from an LLM response."""
    match = _JSON_BLOCK_RE.search(text.strip())
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(match.group())


def classify_transcript(
    llm: BaseChatModel,
    messages: list[BaseMessage],
) -> PatientClassification:
    """Run structured triage extraction without HF function-calling support."""
    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    try:
        payload = extract_json_object(str(content))
        return PatientClassification.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise ValueError(f"Failed to parse classification JSON: {exc}") from exc
