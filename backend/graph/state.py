from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class PatientClassification(BaseModel):
    """Structured extraction schema for clinical transcript analysis."""

    urgency: Literal["low", "medium", "high"] = Field(
        description="Overall urgency level inferred from the clinical dialogue."
    )
    patient_class: list[
        Literal["routine", "pharmacist", "additional test", "urgent"]
    ] = Field(
        description=(
            "One or more triage classes that apply to this patient encounter."
        )
    )
    topic: str = Field(description="Primary clinical topic or chief complaint.")
    summary: str = Field(
        description="Concise clinical summary of the patient encounter."
    )


class OverallState(TypedDict):
    """Global LangGraph state for the medical triage workflow."""

    raw_transcript: str
    dialogue_index: int
    classification: Optional[dict]
    decision_report: Optional[str]
    requires_review: bool
    human_approved: bool
