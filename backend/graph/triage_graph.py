from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.data.loader import load_dialogue_by_index
from backend.graph.state import OverallState
from backend.graph.structured import classify_transcript
from backend.llm import get_llm

SUMMARIZER_SYSTEM_PROMPT = """You are a clinical triage assistant analyzing doctor-patient dialogues.
Extract structured triage information from the transcript.

Reply with ONLY a valid JSON object (no markdown fences) using these keys:
- urgency: one of "low", "medium", "high"
- patient_class: array of one or more of "routine", "pharmacist", "additional test", "urgent"
- topic: string (primary clinical concern)
- summary: string (concise 2-4 sentence clinical summary)

Guidelines:
- urgency: "low" for routine issues, "medium" for same-week follow-up needs,
  "high" for acute or potentially dangerous presentations.
- patient_class: select all applicable classes.
"""

DECISION_SYSTEM_PROMPT = """You are a senior attending physician writing a treatment decision report.
Based on the patient transcript and structured triage classification, produce a comprehensive
clinical decision report that includes:
1. Rationale for the triage decision (why this urgency and patient class)
2. Recommended treatments or interventions
3. Necessary next steps, referrals, and diagnostic tests
4. Patient counseling points and red-flag symptoms to watch for

Write in clear, professional clinical language suitable for handoff to the care team.
"""


def read_transcript_node(state: OverallState) -> dict:
    """Ingest the selected MTS-Dialog row and populate raw_transcript."""
    index = state["dialogue_index"]
    transcript = load_dialogue_by_index(index)
    return {"raw_transcript": transcript}


def clinical_summarizer_node(state: OverallState) -> dict:
    """Analyze transcript with structured output and flag cases needing human review."""
    classification = classify_transcript(
        get_llm(),
        [
            SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Analyze this clinical dialogue:\n\n{state['raw_transcript']}"
            ),
        ],
    )
    classification_dict = classification.model_dump()
    return {
        "classification": classification_dict,
        "requires_review": True,
    }


def human_review_node(state: OverallState) -> dict:
    """Pause for doctor review; accept optional classification edits on resume."""
    review_input = interrupt(
        {
            "message": (
                "Review and edit the AI classification before generating "
                "the decision report."
            ),
            "classification": state.get("classification"),
        }
    )
    if isinstance(review_input, bool):
        review_input = {"approved": review_input}

    if not review_input.get("approved"):
        return {"human_approved": False}

    updates: dict = {"human_approved": True}
    edited = review_input.get("classification")
    if edited:
        updates["classification"] = edited
        updates["requires_review"] = edited.get("urgency") in ("medium", "high")
    return updates


def decision_maker_node(state: OverallState) -> dict:
    """Generate a comprehensive treatment decision report as a senior doctor."""
    llm = get_llm()
    classification = state.get("classification") or {}
    human_message = (
        f"Patient transcript:\n{state['raw_transcript']}\n\n"
        f"Structured classification:\n{classification}\n\n"
        f"Requires human review: {state.get('requires_review', False)}\n"
        f"Human approved: {state.get('human_approved', False)}\n\n"
        "Write the comprehensive treatment decision report."
    )
    response = llm.invoke(
        [
            SystemMessage(content=DECISION_SYSTEM_PROMPT),
            HumanMessage(content=human_message),
        ]
    )
    return {"decision_report": response.content}


def build_triage_graph():
    """Compile the triage LangGraph with MemorySaver checkpointer."""
    builder = StateGraph(OverallState)

    builder.add_node("read_transcript", read_transcript_node)
    builder.add_node("clinical_summarizer", clinical_summarizer_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("decision_maker", decision_maker_node)

    builder.add_edge(START, "read_transcript")
    builder.add_edge("read_transcript", "clinical_summarizer")
    builder.add_edge("clinical_summarizer", "human_review")
    builder.add_edge("human_review", "decision_maker")
    builder.add_edge("decision_maker", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
