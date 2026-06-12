"""
MediTriage AI — LangGraph medical symptom triage agent.

Workflow type: Conditional + Iterative
  - Conditional: routes to emergency / doctor / home-care specialist nodes
  - Iterative: clarification loop + recommendation quality refinement loop
"""

from __future__ import annotations

import os
import re
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

# ---------------------------------------------------------------------------
# Medical knowledge base (used by lookup tool)
# ---------------------------------------------------------------------------

MEDICAL_GUIDELINES: dict[str, dict] = {
    "chest pain": {
        "urgency": "emergency",
        "guidelines": (
            "Chest pain may indicate heart attack, pulmonary embolism, or aortic dissection. "
            "Call emergency services immediately. Do not drive yourself."
        ),
    },
    "difficulty breathing": {
        "urgency": "emergency",
        "guidelines": (
            "Acute shortness of breath can signal asthma attack, anaphylaxis, pneumonia, "
            "or cardiac event. Seek emergency care immediately."
        ),
    },
    "headache": {
        "urgency": "doctor",
        "guidelines": (
            "Headache with fever/stiff neck needs urgent evaluation. "
            "Mild tension headaches: rest, hydration, OTC analgesics. "
            "See a doctor if severe (7+/10), sudden onset, or lasting >3 days."
        ),
    },
    "fever": {
        "urgency": "doctor",
        "guidelines": (
            "Monitor temperature every 4 hours. Stay hydrated. "
            "Seek care if fever >39.4°C, lasts >3 days, or with breathing difficulty."
        ),
    },
    "nausea": {
        "urgency": "home_care",
        "guidelines": (
            "Sip clear fluids, try BRAT diet when tolerated, rest. "
            "See a doctor if unable to keep fluids down 12+ hours or blood in vomit."
        ),
    },
    "cough": {
        "urgency": "home_care",
        "guidelines": (
            "Honey for cough, stay hydrated, rest. "
            "See a doctor if cough >3 weeks, blood in sputum, or high fever."
        ),
    },
    "fatigue": {
        "urgency": "home_care",
        "guidelines": (
            "Ensure adequate sleep and nutrition. "
            "See a doctor if fatigue persists >2 weeks or with unexplained weight loss."
        ),
    },
}


# ---------------------------------------------------------------------------
# Pydantic structured outputs
# ---------------------------------------------------------------------------


class SymptomAnalysis(BaseModel):
    """Structured triage assessment from the LLM."""

    urgency_level: Literal["emergency", "doctor", "home_care"] = Field(
        description="Recommended care level"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence in this assessment (0-1)"
    )
    symptom_category: str = Field(description="Primary symptom category")
    red_flags: list[str] = Field(
        default_factory=list, description="Detected warning signs"
    )
    reasoning: str = Field(description="Brief clinical reasoning")
    clarifying_question: str = Field(
        default="",
        description="Question to ask patient if confidence is low; empty if none needed",
    )


class RecommendationQuality(BaseModel):
    """Quality check on generated recommendation."""

    quality_score: float = Field(ge=0.0, le=1.0)
    is_adequate: bool
    improvement_notes: str = Field(default="")


# ---------------------------------------------------------------------------
# Agent state (TypedDict)
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    symptom: str
    duration: str
    severity: str
    other_symptoms: str
    confidence_score: float
    triage_level: str
    symptom_category: str
    red_flags: list[str]
    reasoning: str
    clarifying_question: str
    tool_results: str
    urgency_score: float
    recommendations: str
    iteration_count: int
    quality_score: float
    assessment_complete: bool
    needs_clarification: bool


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def lookup_medical_guidelines(symptom: str) -> str:
    """Search the medical guidelines database for symptom-specific clinical advice."""
    symptom_lower = symptom.lower()
    matches: list[str] = []
    for key, data in MEDICAL_GUIDELINES.items():
        if key in symptom_lower or symptom_lower in key:
            matches.append(f"[{key.upper()}] (urgency: {data['urgency']})\n{data['guidelines']}")
    if not matches:
        return (
            f"No exact match for '{symptom}'. "
            "General advice: monitor symptoms, rest, hydrate. "
            "Seek medical care if symptoms worsen or persist >3 days."
        )
    return "\n\n".join(matches)


@tool
def calculate_urgency_score(severity: int, duration_days: float, red_flag_count: int) -> str:
    """Calculate a numeric urgency score (1-10) from severity, duration, and red flags."""
    severity = max(1, min(10, severity))
    duration_factor = min(duration_days / 7.0, 2.0)
    score = severity * 0.5 + duration_factor * 1.5 + red_flag_count * 2.0
    score = max(1.0, min(10.0, round(score, 1)))
    level = "EMERGENCY" if score >= 8 else "DOCTOR" if score >= 5 else "HOME CARE"
    return f"Urgency score: {score}/10 → Suggested level: {level}"


TOOLS = [lookup_medical_guidelines, calculate_urgency_score]


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------


def _get_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Copy .env.example to .env and add your Groq API key."
        )
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.2,
        api_key=api_key,
    )


def _parse_severity(severity: str) -> int:
    numbers = re.findall(r"\d+", str(severity))
    if numbers:
        return max(1, min(10, int(numbers[0])))
    return 5


def _parse_duration_days(duration: str) -> float:
    duration_lower = duration.lower()
    numbers = re.findall(r"[\d.]+", duration_lower)
    value = float(numbers[0]) if numbers else 1.0
    if "week" in duration_lower:
        return value * 7
    if "month" in duration_lower:
        return value * 30
    if "hour" in duration_lower:
        return max(value / 24, 0.1)
    return value


def _build_patient_summary(state: AgentState) -> str:
    return (
        f"Primary symptom: {state.get('symptom', 'unknown')}\n"
        f"Duration: {state.get('duration', 'unknown')}\n"
        f"Severity (1-10): {state.get('severity', 'unknown')}\n"
        f"Other symptoms: {state.get('other_symptoms', 'none')}"
    )


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def symptom_analyzer_node(state: AgentState) -> dict:
    """Analyze symptoms with LLM structured output."""
    llm = _get_llm().with_structured_output(SymptomAnalysis)
    patient = _build_patient_summary(state)
    prior = ""
    if state.get("iteration_count", 0) > 0 and state.get("clarifying_question"):
        prior = f"\nPrevious clarifying context: {state['clarifying_question']}"

    prompt = f"""You are a medical triage assistant. Analyze the patient information and classify urgency.

Patient information:
{patient}
{prior}

Rules:
- urgency_level "emergency" for: chest pain, difficulty breathing, stroke signs, severe bleeding, unconsciousness
- urgency_level "doctor" for: fever with headache, persistent/worsening symptoms, severity >= 6
- urgency_level "home_care" for: mild symptoms that can be managed at home
- Set confidence_score below 0.7 if critical information is missing or ambiguous
- If confidence < 0.7, provide a specific clarifying_question

This is for educational triage only — always recommend professional care when in doubt."""

    analysis: SymptomAnalysis = llm.invoke(prompt)

    return {
        "confidence_score": analysis.confidence_score,
        "triage_level": analysis.urgency_level,
        "symptom_category": analysis.symptom_category,
        "red_flags": analysis.red_flags,
        "reasoning": analysis.reasoning,
        "clarifying_question": analysis.clarifying_question,
        "needs_clarification": analysis.confidence_score < 0.7,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def clarification_node(state: AgentState) -> dict:
    """Generate a clarifying question when confidence is low (iterative loop)."""
    question = state.get("clarifying_question") or (
        "Can you describe your symptoms in more detail — when they started, "
        "how severe they are (1-10), and any other symptoms?"
    )
    return {
        "messages": [AIMessage(content=f"🔍 **Clarification needed:** {question}")],
        "needs_clarification": True,
    }


def gather_context_node(state: AgentState) -> dict:
    """Call tools to gather medical guidelines and urgency score."""
    symptom = state.get("symptom", "")
    severity = _parse_severity(state.get("severity", "5"))
    duration_days = _parse_duration_days(state.get("duration", "1 day"))
    red_flags = state.get("red_flags", [])

    guidelines = lookup_medical_guidelines.invoke({"symptom": symptom})
    urgency_result = calculate_urgency_score.invoke(
        {
            "severity": severity,
            "duration_days": duration_days,
            "red_flag_count": len(red_flags),
        }
    )

    urgency_score = 5.0
    match = re.search(r"Urgency score: ([\d.]+)", urgency_result)
    if match:
        urgency_score = float(match.group(1))

    return {
        "tool_results": f"GUIDELINES:\n{guidelines}\n\nURGENCY CALCULATION:\n{urgency_result}",
        "urgency_score": urgency_score,
    }


def emergency_advisor_node(state: AgentState) -> dict:
    """Generate emergency-level recommendations."""
    llm = _get_llm()
    prompt = f"""You are an emergency triage advisor. The patient needs IMMEDIATE emergency care.

Patient:
{_build_patient_summary(state)}

Tool results:
{state.get('tool_results', '')}

Reasoning: {state.get('reasoning', '')}
Red flags: {', '.join(state.get('red_flags', [])) or 'none'}

Write a clear, urgent recommendation. Include:
1. Call emergency services (1122 in Pakistan) immediately
2. What NOT to do
3. While waiting for help

Use markdown. Be direct and calm."""

    response = llm.invoke(prompt)
    return {"recommendations": response.content, "triage_level": "emergency"}


def doctor_advisor_node(state: AgentState) -> dict:
    """Generate doctor-visit recommendations."""
    llm = _get_llm()
    prompt = f"""You are a medical triage advisor recommending a doctor visit within 24-48 hours.

Patient:
{_build_patient_summary(state)}

Tool results:
{state.get('tool_results', '')}

Reasoning: {state.get('reasoning', '')}

Write a helpful markdown recommendation with:
1. Why a doctor visit is recommended
2. Self-care steps until the appointment
3. Red flags that mean go to ER immediately"""

    response = llm.invoke(prompt)
    return {"recommendations": response.content, "triage_level": "doctor"}


def home_care_advisor_node(state: AgentState) -> dict:
    """Generate home-care recommendations."""
    llm = _get_llm()
    prompt = f"""You are a medical triage advisor recommending home care for mild symptoms.

Patient:
{_build_patient_summary(state)}

Tool results:
{state.get('tool_results', '')}

Reasoning: {state.get('reasoning', '')}

Write a helpful markdown home-care plan with:
1. Specific self-care steps
2. What to avoid
3. When to see a doctor if symptoms worsen
4. Expected recovery timeline"""

    response = llm.invoke(prompt)
    return {"recommendations": response.content, "triage_level": "home_care"}


def quality_evaluator_node(state: AgentState) -> dict:
    """Evaluate recommendation quality with structured output."""
    llm = _get_llm().with_structured_output(RecommendationQuality)
    prompt = f"""Evaluate this medical triage recommendation for completeness and safety.

Triage level: {state.get('triage_level')}
Patient: {_build_patient_summary(state)}
Recommendation:
{state.get('recommendations', '')}

Score quality 0-1. Mark is_adequate=False if missing: safety warnings, actionable steps, or when-to-escalate advice.
For emergency cases, is_adequate=False if it doesn't mention calling emergency services."""

    quality: RecommendationQuality = llm.invoke(prompt)
    return {
        "quality_score": quality.quality_score,
        "assessment_complete": quality.is_adequate,
    }


def refine_recommendation_node(state: AgentState) -> dict:
    """Improve recommendation based on quality feedback (iterative loop)."""
    llm = _get_llm()
    prompt = f"""Improve this medical triage recommendation. Make it more complete and actionable.

Patient: {_build_patient_summary(state)}
Triage level: {state.get('triage_level')}
Current recommendation:
{state.get('recommendations', '')}

Tool results: {state.get('tool_results', '')}

Rewrite the full recommendation in markdown. Include all safety warnings and clear next steps."""

    response = llm.invoke(prompt)
    return {
        "recommendations": response.content,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def finalize_node(state: AgentState) -> dict:
    """Mark assessment complete and add summary message."""
    level_labels = {
        "emergency": "🚨 EMERGENCY — Seek immediate care",
        "doctor": "👨‍⚕️ SEE A DOCTOR",
        "home_care": "🏠 HOME CARE",
    }
    label = level_labels.get(state.get("triage_level", ""), "Assessment complete")
    summary = f"""### {label}

**Category:** {state.get('symptom_category', 'N/A')}
**Confidence:** {state.get('confidence_score', 0):.0%}
**Urgency score:** {state.get('urgency_score', 'N/A')}/10

---

{state.get('recommendations', '')}

---

*Educational triage only. Always consult a healthcare professional for medical advice.*
"""
    return {
        "messages": [AIMessage(content=summary)],
        "assessment_complete": True,
        "needs_clarification": False,
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------


def after_analysis_route(state: AgentState) -> str:
    """Route after symptom analysis: clarify, or proceed to gather context."""
    if state.get("needs_clarification") and state.get("iteration_count", 0) < 4:
        return "clarify"
    return "gather"


def triage_level_route(state: AgentState) -> str:
    """Conditional routing to specialist advisor nodes."""
    level = state.get("triage_level", "home_care")
    if level == "emergency":
        return "emergency"
    if level == "doctor":
        return "doctor"
    return "home_care"


def after_quality_route(state: AgentState) -> str:
    """Loop to refine if quality is low, otherwise finalize."""
    if not state.get("assessment_complete") and state.get("iteration_count", 0) < 6:
        return "refine"
    return "finalize"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def create_graph():
    """Build and compile the MediTriage LangGraph agent with MemorySaver."""
    workflow = StateGraph(AgentState)

    workflow.add_node("symptom_analyzer", symptom_analyzer_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("emergency_advisor", emergency_advisor_node)
    workflow.add_node("doctor_advisor", doctor_advisor_node)
    workflow.add_node("home_care_advisor", home_care_advisor_node)
    workflow.add_node("quality_evaluator", quality_evaluator_node)
    workflow.add_node("refine_recommendation", refine_recommendation_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("symptom_analyzer")

    workflow.add_conditional_edges(
        "symptom_analyzer",
        after_analysis_route,
        {"clarify": "clarification", "gather": "gather_context"},
    )
    workflow.add_edge("clarification", "symptom_analyzer")

    workflow.add_conditional_edges(
        "gather_context",
        triage_level_route,
        {
            "emergency": "emergency_advisor",
            "doctor": "doctor_advisor",
            "home_care": "home_care_advisor",
        },
    )

    workflow.add_edge("emergency_advisor", "quality_evaluator")
    workflow.add_edge("doctor_advisor", "quality_evaluator")
    workflow.add_edge("home_care_advisor", "quality_evaluator")

    workflow.add_conditional_edges(
        "quality_evaluator",
        after_quality_route,
        {"refine": "refine_recommendation", "finalize": "finalize"},
    )
    workflow.add_edge("refine_recommendation", "quality_evaluator")
    workflow.add_edge("finalize", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def make_initial_state(
    symptom: str,
    duration: str,
    severity: str,
    other_symptoms: str,
) -> AgentState:
    """Create a fresh agent state for a new assessment."""
    return AgentState(
        messages=[HumanMessage(content=f"Symptom assessment: {symptom}")],
        symptom=symptom,
        duration=duration,
        severity=severity,
        other_symptoms=other_symptoms,
        confidence_score=0.0,
        triage_level="",
        symptom_category="",
        red_flags=[],
        reasoning="",
        clarifying_question="",
        tool_results="",
        urgency_score=0.0,
        recommendations="",
        iteration_count=0,
        quality_score=0.0,
        assessment_complete=False,
        needs_clarification=False,
    )


def run_assessment(
    graph,
    symptom: str,
    duration: str,
    severity: str,
    other_symptoms: str,
    thread_id: str,
) -> AgentState:
    """Run a full triage assessment through the LangGraph agent."""
    state = make_initial_state(symptom, duration, severity, other_symptoms)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config)


def get_assessment_history(graph, thread_id: str) -> list[dict]:
    """Retrieve past assessments from graph memory for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
        if snapshot and snapshot.values:
            return [
                {
                    "symptom": snapshot.values.get("symptom", ""),
                    "triage": snapshot.values.get("triage_level", ""),
                    "severity": snapshot.values.get("severity", ""),
                }
            ]
    except Exception:
        pass
    return []
