import uuid
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from langgraph.types import Command
from pydantic import BaseModel, Field

from backend.config import get_allowed_origins
from backend.data.loader import get_dialogue_count, list_observation_options
from backend.graph.state import PatientClassification
from backend.graph.triage_graph import build_triage_graph
from backend.graph.visualization import (
    GRAPH_NODE_DETAILS,
    get_triage_graph_png,
    get_triage_mermaid,
)

app = FastAPI(
    title="Medical Triage Multi-Agent API",
    description="LangGraph-powered clinical triage with human-in-the-loop review.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

triage_graph = build_triage_graph()


class StartTriageRequest(BaseModel):
    dialogue_index: int = Field(
        ...,
        ge=0,
        description="0-based row index in the MTS-Dialog validation CSV.",
    )


class ClassificationUpdate(BaseModel):
    urgency: Literal["low", "medium", "high"]
    patient_class: list[
        Literal["routine", "pharmacist", "additional test", "urgent"]
    ]
    topic: str
    summary: str


class ApproveTriageRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID returned by /start_triage.")
    approved: bool = Field(
        default=True,
        description="Whether the reviewing doctor approves proceeding to decision.",
    )
    classification: Optional[ClassificationUpdate] = Field(
        default=None,
        description="Doctor-edited classification fields to use for the decision report.",
    )


class UpdateReportRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID for the triage session.")
    decision_report: str = Field(
        ...,
        min_length=1,
        description="Doctor-edited clinical decision report text.",
    )


def _graph_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _serialize_interrupt(interrupts: list) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "value": item.value,
        }
        for item in interrupts
    ]


def _build_response(thread_id: str, result: dict) -> dict[str, Any]:
    interrupts = result.get("__interrupt__")
    if interrupts:
        return {
            "thread_id": thread_id,
            "status": "awaiting_approval",
            "raw_transcript": result.get("raw_transcript"),
            "classification": result.get("classification"),
            "requires_review": result.get("requires_review", True),
            "human_approved": result.get("human_approved", False),
            "decision_report": result.get("decision_report"),
            "interrupt": _serialize_interrupt(interrupts),
        }

    return {
        "thread_id": thread_id,
        "status": "completed",
        "raw_transcript": result.get("raw_transcript"),
        "classification": result.get("classification"),
        "requires_review": result.get("requires_review", True),
        "human_approved": result.get("human_approved", False),
        "decision_report": result.get("decision_report"),
        "interrupt": None,
    }


def _state_response(thread_id: str, values: dict) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "status": "completed" if values.get("decision_report") else "awaiting_approval",
        "raw_transcript": values.get("raw_transcript"),
        "classification": values.get("classification"),
        "requires_review": values.get("requires_review", True),
        "human_approved": values.get("human_approved", False),
        "decision_report": values.get("decision_report"),
        "interrupt": None,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dataset/info")
def dataset_info() -> dict[str, int]:
    return {"dialogue_count": get_dialogue_count()}


@app.get("/dataset/observations")
def dataset_observations() -> dict[str, list[dict[str, int | str]]]:
    return {"observations": list_observation_options()}


@app.get("/graph/mermaid")
def graph_mermaid() -> dict[str, str]:
    return {"mermaid": get_triage_mermaid()}


@app.get("/graph/info")
def graph_info() -> dict[str, list[dict[str, str]]]:
    return {"nodes": GRAPH_NODE_DETAILS}


@app.get("/graph/png")
def graph_png() -> Response:
    return Response(content=get_triage_graph_png(), media_type="image/png")


@app.post("/start_triage")
def start_triage(request: StartTriageRequest) -> dict[str, Any]:
    """Run triage until completion or human-review interrupt."""
    try:
        get_dialogue_count()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load dataset: {exc}") from exc

    if request.dialogue_index >= get_dialogue_count():
        raise HTTPException(
            status_code=400,
            detail=(
                f"dialogue_index {request.dialogue_index} is out of range. "
                f"Valid indices: 0..{get_dialogue_count() - 1}"
            ),
        )

    thread_id = str(uuid.uuid4())
    initial_state = {
        "raw_transcript": "",
        "dialogue_index": request.dialogue_index,
        "classification": None,
        "decision_report": None,
        "requires_review": True,
        "human_approved": False,
    }

    try:
        result = triage_graph.invoke(initial_state, config=_graph_config(thread_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Triage graph failed: {exc}") from exc

    return _build_response(thread_id, result)


@app.post("/approve_triage")
def approve_triage(request: ApproveTriageRequest) -> dict[str, Any]:
    """Resume an interrupted triage thread into decision_maker_node."""
    if not request.approved:
        raise HTTPException(
            status_code=400,
            detail="Triage was not approved. Set approved=true to continue.",
        )

    config = _graph_config(request.thread_id)
    snapshot = triage_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"No triage session found for thread_id '{request.thread_id}'.",
        )

    if snapshot.next and "decision_maker" in snapshot.next:
        pass
    elif snapshot.values.get("decision_report"):
        return _state_response(request.thread_id, snapshot.values)
    elif not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="Triage session is not waiting for approval.",
        )

    resume_payload: dict[str, Any] = {"approved": request.approved}
    if request.classification is not None:
        validated = PatientClassification.model_validate(
            request.classification.model_dump()
        )
        resume_payload["classification"] = validated.model_dump()

    try:
        result = triage_graph.invoke(
            Command(resume=resume_payload),
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume triage: {exc}",
        ) from exc

    return _build_response(request.thread_id, result)


@app.post("/update_report")
def update_report(request: UpdateReportRequest) -> dict[str, Any]:
    """Persist doctor edits to the generated clinical decision report."""
    config = _graph_config(request.thread_id)
    snapshot = triage_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"No triage session found for thread_id '{request.thread_id}'.",
        )
    if not snapshot.values.get("decision_report"):
        raise HTTPException(
            status_code=400,
            detail="Decision report has not been generated yet.",
        )

    triage_graph.update_state(
        config,
        {"decision_report": request.decision_report.strip()},
    )
    updated = triage_graph.get_state(config).values
    return _state_response(request.thread_id, updated)
