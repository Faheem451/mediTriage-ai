"""MediTriage AI — Streamlit interface for the LangGraph triage agent."""

from datetime import datetime
import re

import streamlit as st

from agent import create_graph, run_assessment

st.set_page_config(page_title="MediTriage AI", page_icon="🏥", layout="wide")

st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .emergency { border-left: 5px solid #e74c3c; padding-left: 1rem; }
    .doctor { border-left: 5px solid #f39c12; padding-left: 1rem; }
    .home { border-left: 5px solid #3498db; padding-left: 1rem; }
    .graph-badge {
        background: #eef2ff;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-header"><h1>🏥 MediTriage AI</h1>'
    "<p>LangGraph-powered medical symptom triage</p></div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []
if "step" not in st.session_state:
    st.session_state.step = 0
if "patient_symptom" not in st.session_state:
    st.session_state.patient_symptom = ""
if "patient_duration" not in st.session_state:
    st.session_state.patient_duration = ""
if "patient_severity" not in st.session_state:
    st.session_state.patient_severity = ""
if "patient_other" not in st.session_state:
    st.session_state.patient_other = ""
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if "last_triage_level" not in st.session_state:
    st.session_state.last_triage_level = ""


@st.cache_resource
def get_graph():
    return create_graph()


def is_memory_question(user_input: str) -> bool:
    keywords = [
        "what did i",
        "what was my",
        "remember",
        "recall",
        "previous",
        "before",
        "earlier",
        "last time",
        "tell you before",
    ]
    return any(kw in user_input.lower() for kw in keywords)


def recall_previous_conversation() -> str:
    if not st.session_state.conversation_history:
        return "We haven't completed any assessments yet. Describe your symptoms to start."
    last = st.session_state.conversation_history[-1]
    return f"""### 🧠 Memory recall (thread: `{st.session_state.thread_id[:20]}...`)

**Last assessment:**
- **Symptom:** {last['symptom']}
- **Duration:** {last['duration']}
- **Severity:** {last['severity']}/10
- **Other symptoms:** {last['other']}
- **Triage level:** {last['triage']}
- **Time:** {last['timestamp']}

Start a new assessment anytime by describing a symptom.
"""


def triage_css_class(level: str) -> str:
    return {"emergency": "emergency", "doctor": "doctor"}.get(level, "home")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🏥 MediTriage AI")
    st.markdown("*LangGraph Conditional + Iterative workflow*")
    st.markdown("---")
    st.markdown("### 🧠 Memory (MemorySaver)")
    st.markdown(f"**Thread ID:** `{st.session_state.thread_id}`")
    st.markdown(f"**Assessments:** {len(st.session_state.conversation_history)}")
    if st.session_state.conversation_history:
        for i, conv in enumerate(st.session_state.conversation_history[-3:], 1):
            st.markdown(f"{i}. {conv['symptom'][:28]} → **{conv['triage']}**")
    st.markdown("---")
    st.markdown("### 📋 LangGraph nodes")
    st.markdown(
        """
1. Symptom Analyzer (structured output)
2. Clarification loop
3. Tool context (guidelines + urgency)
4. Specialist advisor (conditional route)
5. Quality evaluator loop
6. Finalize
"""
    )
    st.markdown("---")
    st.markdown("### 💡 Demo inputs")
    st.markdown("- **Emergency:** `I have chest pain and can't breathe`")
    st.markdown("- **Home care:** `Mild headache for 1 day, severity 3`")
    st.markdown("---")
    if st.button("🔄 Start Fresh", use_container_width=True):
        st.session_state.messages = []
        st.session_state.step = 0
        st.session_state.patient_symptom = ""
        st.session_state.patient_duration = ""
        st.session_state.patient_severity = ""
        st.session_state.patient_other = ""
        st.session_state.conversation_history = []
        st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.last_triage_level = ""
        st.rerun()
    st.caption("⚠️ Educational only. Not a substitute for professional medical advice.")

# ---------------------------------------------------------------------------
# Chat display
# ---------------------------------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message.get("triage_level"):
            st.markdown(
                f'<div class="{triage_css_class(message["triage_level"])}">',
                unsafe_allow_html=True,
            )
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("triage_level"):
            st.markdown("</div>", unsafe_allow_html=True)

if len(st.session_state.messages) == 0:
    greeting = """Hello! I'm **MediTriage AI**, powered by a **LangGraph** agent with Groq LLM.

**How it works:**
1. Describe your main symptom
2. Answer 3 follow-up questions (duration, severity, other symptoms)
3. The agent analyzes, routes you (emergency / doctor / home care), uses medical tools, and refines its recommendation

**Try:** "I have chest pain" vs "mild headache" to see **conditional routing** in action.

Describe your main symptom to begin:"""
    with st.chat_message("assistant"):
        st.markdown(greeting)
    st.session_state.messages.append({"role": "assistant", "content": greeting})

# ---------------------------------------------------------------------------
# User input
# ---------------------------------------------------------------------------

user_input = st.chat_input("Type your response here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if is_memory_question(user_input):
        memory_response = recall_previous_conversation()
        with st.chat_message("assistant"):
            st.markdown(memory_response)
        st.session_state.messages.append({"role": "assistant", "content": memory_response})

    else:
        step = st.session_state.step

        if step == 0:
            st.session_state.patient_symptom = user_input
            response = (
                "📋 **Question 1 of 3:** How long have you had these symptoms? "
                "(e.g. '2 days', '1 week')"
            )
            st.session_state.step = 1
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        elif step == 1:
            st.session_state.patient_duration = user_input
            response = (
                "📊 **Question 2 of 3:** Severity from 1–10? "
                "(1 = very mild, 10 = worst possible)"
            )
            st.session_state.step = 2
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        elif step == 2:
            numbers = re.findall(r"\d+", user_input)
            st.session_state.patient_severity = numbers[0] if numbers else user_input
            response = (
                "🔍 **Question 3 of 3:** Any other symptoms? "
                "(e.g. fever, nausea — or 'none')"
            )
            st.session_state.step = 3
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        elif step == 3:
            st.session_state.patient_other = user_input
            st.session_state.step = 0

            with st.chat_message("assistant"):
                st.markdown(
                    '<div class="graph-badge">⏳ Running LangGraph agent '
                    "(analyze → route → tools → quality loop)...</div>",
                    unsafe_allow_html=True,
                )

                try:
                    graph = get_graph()
                    assessment_thread = (
                        f"{st.session_state.thread_id}_{len(st.session_state.conversation_history)}"
                    )

                    with st.spinner("Agent is thinking..."):
                        result = run_assessment(
                            graph,
                            st.session_state.patient_symptom,
                            st.session_state.patient_duration,
                            st.session_state.patient_severity,
                            st.session_state.patient_other,
                            assessment_thread,
                        )

                    triage_level = result.get("triage_level", "home_care")
                    st.session_state.last_triage_level = triage_level

                    level_emoji = {
                        "emergency": "🚨",
                        "doctor": "👨‍⚕️",
                        "home_care": "🏠",
                    }
                    header = f"""### {level_emoji.get(triage_level, '📋')} Assessment complete

| Field | Value |
|-------|-------|
| **Symptom** | {st.session_state.patient_symptom} |
| **Duration** | {st.session_state.patient_duration} |
| **Severity** | {st.session_state.patient_severity}/10 |
| **Other** | {st.session_state.patient_other} |
| **Category** | {result.get('symptom_category', 'N/A')} |
| **Confidence** | {result.get('confidence_score', 0):.0%} |
| **Urgency score** | {result.get('urgency_score', 'N/A')}/10 |
| **Graph iterations** | {result.get('iteration_count', 0)} |
| **Quality score** | {result.get('quality_score', 0):.0%} |

**Routing:** `{triage_level}` (conditional edge)

---

{result.get('recommendations', 'No recommendation generated.')}

---

*Ask "What did I tell you before?" to test MemorySaver recall.*
"""

                    st.markdown(
                        f'<div class="{triage_css_class(triage_level)}">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(header)
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": header,
                            "triage_level": triage_level,
                        }
                    )

                    st.session_state.conversation_history.append(
                        {
                            "symptom": st.session_state.patient_symptom,
                            "duration": st.session_state.patient_duration,
                            "severity": st.session_state.patient_severity,
                            "other": st.session_state.patient_other,
                            "triage": triage_level,
                            "timestamp": datetime.now().strftime("%I:%M %p"),
                        }
                    )

                except ValueError as exc:
                    error_msg = f"**Configuration error:** {exc}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
                except Exception as exc:
                    error_msg = (
                        f"**Agent error:** {exc}\n\n"
                        "Check your GROQ_API_KEY in `.env` and try again."
                    )
                    st.error(str(exc))
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

            st.session_state.patient_symptom = ""
            st.session_state.patient_duration = ""
            st.session_state.patient_severity = ""
            st.session_state.patient_other = ""
