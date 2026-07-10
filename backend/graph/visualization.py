from functools import lru_cache

from backend.graph.triage_graph import build_triage_graph

GRAPH_NODE_DETAILS = [
    {
        "node": "read_transcript",
        "agent": "Data Loader",
        "description": "Ingests the selected MTS-Dialog row and sets raw_transcript.",
    },
    {
        "node": "clinical_summarizer",
        "agent": "Clinical Summarizer",
        "description": "Llama extracts structured PatientClassification JSON from the transcript.",
    },
    {
        "node": "human_review",
        "agent": "Human Review (HITL)",
        "description": "Pauses for doctor edits to classification; resumes on approval.",
    },
    {
        "node": "decision_maker",
        "agent": "Decision Maker",
        "description": "Senior-doctor LLM generates the treatment decision report.",
    },
]


@lru_cache
def get_triage_mermaid() -> str:
    return build_triage_graph().get_graph().draw_mermaid()


@lru_cache
def get_triage_graph_png() -> bytes:
    return build_triage_graph().get_graph().draw_mermaid_png()
