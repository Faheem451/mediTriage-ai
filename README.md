# MediTriage AI — LangGraph Medical Symptom Checker

MediTriage AI is a LangGraph-powered medical triage agent that analyzes patient symptoms, uses medical tools, routes to the appropriate care level, and iteratively refines its recommendations using a Groq LLM.

## Problem

People often struggle to decide whether symptoms need emergency care, a doctor visit, or home management. MediTriage AI provides structured, AI-generated triage guidance for educational purposes.

## Workflow Type

**Conditional + Iterative**

| Type | How it is used |
|------|----------------|
| **Conditional** | After analysis, the graph routes to `emergency_advisor`, `doctor_advisor`, or `home_care_advisor` based on urgency |
| **Iterative** | Clarification loop (low confidence → re-analyze) and quality refinement loop (low quality → refine → re-evaluate) |

## LangGraph Features

| Feature | Implementation |
|---------|----------------|
| TypedDict state | `AgentState` in `agent.py` |
| Meaningful nodes | 9 nodes: analyzer, clarification, gather_context, 3 advisors, quality_evaluator, refine, finalize |
| Conditional edges | Urgency routing + quality routing |
| Loop | Clarification loop + recommendation refinement loop |
| Tool use | `lookup_medical_guidelines`, `calculate_urgency_score` |
| MemorySaver | `thread_id` per assessment session |
| Structured output | `SymptomAnalysis`, `RecommendationQuality` (Pydantic + `with_structured_output`) |
| Streamlit UI | `app.py` |

## Graph Architecture

```
symptom_analyzer
    ├─[confidence < 0.7]─→ clarification ──→ (loop back)
    └─[else]─→ gather_context (tools)
                    ├─[emergency]─→ emergency_advisor ──┐
                    ├─[doctor]────→ doctor_advisor ─────┼─→ quality_evaluator
                    └─[home_care]─→ home_care_advisor ──┘
                                              ├─[low quality]─→ refine ──→ (loop)
                                              └─[adequate]────→ finalize → END
```

See `flowchart/medigraph.png` for the visual diagram.

## Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd mediTriage-ai
pip install -r requirements.txt
```

### 2. Configure API key

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:

```
GROQ_API_KEY=gsk_your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

### 4. Run the Jupyter notebook

```bash
jupyter notebook agent.ipynb
```

Run all cells to see the graph visualization via `draw_mermaid_png()`.

## Demo Scenarios (for presentation)

1. **Emergency branching:** `I have chest pain and difficulty breathing` → routes to emergency advisor
2. **Home care branching:** `Mild headache for 1 day, severity 3, no other symptoms` → routes to home care advisor
3. **Memory:** Complete an assessment, then ask `What did I tell you before?`

## Repository Structure

```
mediTriage-ai/
├── agent.py           # LangGraph agent (graph, tools, state)
├── app.py             # Streamlit interface
├── agent.ipynb        # Notebook with graph visualization
├── requirements.txt
├── .env.example
├── flowchart/         # Agent flowchart image
├── slides/            # Presentation slides
└── README.md
```

## Group Members

| Name | Role |
|------|------|
| _Fill in_ | _Fill in_ |

## Disclaimer

This agent is for **educational purposes only**. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.
