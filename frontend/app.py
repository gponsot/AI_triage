"""Medical triage demo dashboard."""

import html
import os
import time
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def get_api_base() -> str:
    """Resolve API URL for local .env or Streamlit Cloud secrets."""
    try:
        if "TRIAGE_API_URL" in st.secrets:
            return str(st.secrets["TRIAGE_API_URL"]).rstrip("/")
    except Exception:
        pass
    return os.getenv("TRIAGE_API_URL", "http://127.0.0.1:8000").rstrip("/")

URGENCY_OPTIONS = ["low", "medium", "high"]
PATIENT_CLASS_OPTIONS = ["routine", "pharmacist", "additional test", "urgent"]

URGENCY_STYLES = {
    "low": {
        "accent": "#16a34a",
        "bg": "#ecfdf3",
        "border": "#86efac",
        "badge_bg": "#dcfce7",
    },
    "medium": {
        "accent": "#d97706",
        "bg": "#fff7ed",
        "border": "#fdba74",
        "badge_bg": "#ffedd5",
    },
    "high": {
        "accent": "#dc2626",
        "bg": "#fef2f2",
        "border": "#fca5a5",
        "badge_bg": "#fee2e2",
    },
}


def _urgency_style(urgency: str) -> dict[str, str]:
    return URGENCY_STYLES.get(urgency, URGENCY_STYLES["medium"])


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        .panel-card {
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            min-height: 420px;
        }
        .panel-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #475569;
            margin-bottom: 0.75rem;
        }
        .edit-panel {
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            min-height: 420px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        }
        .classification-card {
            border-radius: 14px;
            padding: 1.25rem;
            min-height: 420px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        }
        .classification-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        .classification-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .urgency-pill {
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .class-chip {
            display: inline-block;
            margin: 0.2rem 0.35rem 0.2rem 0;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(15, 23, 42, 0.08);
            font-size: 0.85rem;
            font-weight: 600;
        }
        .field-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            opacity: 0.8;
            margin-top: 0.9rem;
            margin-bottom: 0.35rem;
        }
        .field-value {
            font-size: 1rem;
            line-height: 1.55;
        }
        .report-card {
            border-radius: 14px;
            padding: 1.5rem 1.75rem;
            border: 1px solid #dbeafe;
            background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
            box-shadow: 0 10px 28px rgba(37, 99, 235, 0.08);
        }
        .hero-strip {
            border-radius: 14px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
            color: white;
        }
        .hero-strip h1 {
            color: white !important;
            font-size: 1.8rem !important;
            margin-bottom: 0.2rem !important;
        }
        .hero-strip p {
            margin: 0;
            opacity: 0.92;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_classification_card(classification: dict) -> None:
    urgency = classification.get("urgency", "medium")
    style = _urgency_style(urgency)
    patient_classes = classification.get("patient_class") or []
    chips = "".join(
        f'<span class="class-chip">{html.escape(str(label))}</span>'
        for label in patient_classes
    ) or '<span class="field-value">—</span>'

    topic = html.escape(str(classification.get("topic", "—")))
    summary = html.escape(str(classification.get("summary", "—")))

    st.markdown(
        f"""
        <div class="classification-card" style="
            background: {style['bg']};
            border: 1px solid {style['border']};
        ">
            <div class="classification-header">
                <div class="classification-title" style="color: {style['accent']};">
                    Classification
                </div>
                <span class="urgency-pill" style="
                    color: {style['accent']};
                    background: {style['badge_bg']};
                    border: 1px solid {style['border']};
                ">{urgency} urgency</span>
            </div>
            <div class="field-label" style="color: {style['accent']};">Patient Class</div>
            <div>{chips}</div>
            <div class="field-label" style="color: {style['accent']};">Topic</div>
            <div class="field-value">{topic}</div>
            <div class="field-label" style="color: {style['accent']};">Summary</div>
            <div class="field-value">{summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_transcript_card(transcript: str) -> None:
    safe_transcript = html.escape(transcript).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-title">Clinical Transcript</div>
            <div class="field-value">{safe_transcript}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _api_request(method: str, url: str, **kwargs) -> requests.Response:
    """Call the API with retries for Render free-tier cold starts."""
    timeout = kwargs.pop("timeout", 120)
    retries = kwargs.pop("retries", 3)
    last_error: requests.RequestException | None = None

    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))

    if last_error is not None:
        raise last_error
    raise requests.RequestException("API request failed")


def _fetch_observations(api_base: str) -> list[dict]:
    response = _api_request("GET", f"{api_base}/dataset/observations")
    return response.json()["observations"]


def _render_classification_editor(classification: dict, thread_id: str) -> dict | None:
    """Render editable classification fields; return payload when submitted."""
    urgency = classification.get("urgency", "medium")
    style = _urgency_style(urgency)

    st.markdown(
        f"""
        <div class="edit-panel" style="
            background: {style['bg']};
            border: 1px solid {style['border']};
        ">
            <div class="classification-title" style="color: {style['accent']}; margin-bottom: 0.5rem;">
                Edit Classification
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(f"classification_form_{thread_id}"):
        selected_urgency = st.selectbox(
            "Urgency",
            URGENCY_OPTIONS,
            index=URGENCY_OPTIONS.index(urgency)
            if urgency in URGENCY_OPTIONS
            else 1,
        )
        selected_classes = st.multiselect(
            "Patient class",
            PATIENT_CLASS_OPTIONS,
            default=[
                value
                for value in (classification.get("patient_class") or [])
                if value in PATIENT_CLASS_OPTIONS
            ]
            or ["routine"],
        )
        topic = st.text_input("Topic", value=classification.get("topic", ""))
        summary = st.text_area(
            "Summary",
            value=classification.get("summary", ""),
            height=140,
        )
        submitted = st.form_submit_button(
            "Approve & Generate Report",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None

    if not selected_classes:
        st.error("Select at least one patient class before approving.")
        return None

    return {
        "approved": True,
        "classification": {
            "urgency": selected_urgency,
            "patient_class": selected_classes,
            "topic": topic.strip(),
            "summary": summary.strip(),
        },
    }


def _current_graph_step(triage: dict | None) -> str:
    if not triage:
        return "Idle — run **Start Triage** to execute the graph."
    if triage.get("status") == "awaiting_approval":
        return "Paused at **human_review** (doctor editing classification)."
    if triage.get("decision_report"):
        return "Completed — graph reached **decision_maker** and finished."
    return "In progress."


def _render_graph_tab(api_base: str, triage: dict | None) -> None:
    st.subheader("LangGraph Agent Workflow")
    st.markdown(_current_graph_step(triage))

    try:
        with st.spinner("Loading graph visualization..."):
            info_resp = _api_request("GET", f"{api_base}/graph/info")
            png_resp = _api_request("GET", f"{api_base}/graph/png")
    except requests.RequestException as exc:
        st.error(f"Could not load graph from API: {exc}")
        return

    nodes = info_resp.json()["nodes"]

    viz_col, info_col = st.columns([1.4, 1], gap="large")
    with viz_col:
        st.markdown(
            """
            <div class="panel-card" style="min-height: auto; padding-bottom: 0.5rem;">
                <div class="panel-title">Workflow Diagram</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.image(png_resp.content, use_container_width=True)

        with st.expander("View Mermaid source"):
            try:
                mermaid_resp = _api_request("GET", f"{api_base}/graph/mermaid")
                st.code(mermaid_resp.json()["mermaid"], language="text")
            except requests.RequestException:
                st.caption("Mermaid source unavailable.")

    with info_col:
        st.markdown(
            """
            <div class="panel-card" style="min-height: auto;">
                <div class="panel-title">Agent Nodes</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for node in nodes:
            st.markdown(f"**{node['agent']}** (`{node['node']}`)")
            st.write(node["description"])
            st.divider()


st.set_page_config(
    page_title="Medical Triage Demo",
    page_icon="🩺",
    layout="wide",
)
_inject_styles()

api_base = get_api_base()

if api_base.startswith("http://127.0.0.1") or api_base.startswith("http://localhost"):
    st.warning(
        "Backend URL is still set to localhost. On Streamlit Cloud, add "
        "`TRIAGE_API_URL` in **App settings → Secrets** pointing to your deployed FastAPI URL."
    )

st.markdown(
    """
    <div class="hero-strip">
        <h1>Medical Triage Multi-Agent Demo</h1>
        <p>Review clinical dialogues, inspect AI classification, and approve treatment decisions. A prototype application
        built with LangGraph and Streamlit, to aid doctors in recording electronic health record (EHR) data and triage AI classification.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(f"API: `{api_base}`")

try:
    with st.spinner(
        "Connecting to backend... Render free tier may take up to 60 seconds to wake up."
    ):
        observations = _fetch_observations(api_base)
except requests.RequestException as exc:
    st.error(f"Cannot reach backend at {api_base}: {exc}")
    st.info(
        "If you're on Render's free tier, open "
        f"[{api_base}/health]({api_base}/health) in a new tab to wake the API, "
        "wait ~60 seconds, then refresh this page."
    )
    st.stop()

if not observations:
    st.warning("No observations available in the dataset sample.")
    st.stop()

labels = [str(item["label"]) for item in observations]
label_to_index = {str(item["label"]): int(item["index"]) for item in observations}

control_left, control_right = st.columns([4, 1], gap="medium")
with control_left:
    selected_label = st.selectbox(
        "Select clinical observation",
        options=labels,
        index=0,
    )
with control_right:
    st.write("")
    start_clicked = st.button("Start Triage", type="primary", use_container_width=True)

dialogue_index = label_to_index[selected_label]

if start_clicked:
    try:
        with st.spinner("Running triage agents..."):
            resp = _api_request(
                "POST",
                f"{api_base}/start_triage",
                json={"dialogue_index": dialogue_index},
                timeout=300,
            )
        st.session_state["triage"] = resp.json()
        st.session_state["selected_observation"] = selected_label
    except requests.RequestException as exc:
        st.error(f"Triage failed: {exc}")
        st.stop()

triage = st.session_state.get("triage")

tab_review, tab_report, tab_graph = st.tabs(
    ["Triage Review", "Decision Report", "Agent Graph"]
)

with tab_graph:
    _render_graph_tab(api_base, triage)

if not triage:
    with tab_review:
        st.info("Choose an observation from the dropdown and click **Start Triage**.")
    with tab_report:
        st.info("Run triage to generate a clinical decision report.")
    st.stop()

with tab_review:
    if triage.get("status") == "awaiting_approval":
        st.info(
            "Review and edit the AI classification below. "
            "When you approve, the decision report will be generated using your changes."
        )

    transcript_col, classification_col = st.columns([1.35, 1], gap="large")

    with transcript_col:
        _render_transcript_card(triage.get("raw_transcript", ""))

    with classification_col:
        classification = triage.get("classification") or {}
        if triage.get("status") == "awaiting_approval" and classification:
            approval_payload = _render_classification_editor(
                classification,
                triage["thread_id"],
            )
            if approval_payload:
                with st.spinner("Generating decision report..."):
                    resp = requests.post(
                        f"{api_base}/approve_triage",
                        json={
                            "thread_id": triage["thread_id"],
                            **approval_payload,
                        },
                        timeout=300,
                    )
                if resp.ok:
                    st.session_state["triage"] = resp.json()
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", resp.text))
        elif classification:
            _render_classification_card(classification)
        else:
            st.markdown(
                """
                <div class="panel-card">
                    <div class="panel-title">Classification</div>
                    <div class="field-value">No classification available yet.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with tab_report:
    decision_report = triage.get("decision_report")
    status = triage.get("status")

    if decision_report:
        st.markdown(
            """
            <div class="report-card">
                <div class="panel-title" style="color:#1d4ed8;">Clinical Decision Report</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("You can rewrite the report below and save your changes.")
        edited_report = st.text_area(
            "Decision report",
            value=decision_report,
            height=420,
            label_visibility="collapsed",
            key=f"report_editor_{triage['thread_id']}",
        )
        save_col, _ = st.columns([1, 3])
        with save_col:
            if st.button("Save Report Changes", use_container_width=True):
                with st.spinner("Saving report..."):
                    resp = requests.post(
                        f"{api_base}/update_report",
                        json={
                            "thread_id": triage["thread_id"],
                            "decision_report": edited_report,
                        },
                        timeout=60,
                    )
                if resp.ok:
                    st.session_state["triage"] = resp.json()
                    st.success("Report updated.")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", resp.text))
    elif status == "awaiting_approval":
        st.info(
            "The decision report will appear here after you review and approve "
            "the classification on the **Triage Review** tab."
        )
    else:
        st.info("Run triage to generate a clinical decision report.")
