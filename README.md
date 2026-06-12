# 🏥 MediTriage AI - Smart Symptom Checker

## Agent Description
MediTriage AI is a LangGraph-powered medical triage agent that analyzes symptoms, asks clarifying questions, and routes patients to appropriate care levels (home care, doctor visit, or emergency room).

## Workflow Type
**Conditional + Iterative** - Primary workflow is Conditional (routes based on severity) with an Iterative loop for symptom clarification.

## LangGraph Features Used
- ✅ State management with TypedDict
- ✅ 4 meaningful nodes (SymptomAnalyzer, Clarifier, TriageRouter, ResourceGenerator)
- ✅ Conditional edges (severity-based routing)
- ✅ Iterative loop (clarification until confidence > 0.7)
- ✅ Tool use (medical database search)
- ✅ MemorySaver with thread_id
- ✅ Pydantic structured output
- ✅ Streamlit interface

## Setup Instructions

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd mediTriage-ai