# Hotel Customer Care Agentic AI System — Project Plan

## Context
Build a multi-agent AI system for hotel customer care that handles booking, amenities, billing, complaints, and general queries. The system includes full observability via Langfuse to monitor agent performance, trace queries end-to-end, track costs, and evaluate response quality.

## Chosen Stack (Open Source)
| Component | Tool | Why |
|-----------|------|-----|
| Agent Framework | **LangGraph** | Production-ready, graph-based stateful workflows, best for multi-agent routing |
| Observability | **Langfuse** | MIT licensed, end-to-end tracing, evaluations, prompt management, cost tracking |
| LLM | **OpenAI GPT-4o** | Best balance of quality/cost for customer care |
| Vector DB | **ChromaDB** | Lightweight, open-source, embedded — hotel knowledge base |
| API | **FastAPI** | Async, fast, auto-docs |
| Language | **Python 3.11+** | |

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  User Query  │────▶│  FastAPI  /chat  endpoint                    │
└─────────────┘     └──────────┬───────────────────────────────────┘
                               │  (Langfuse trace created)
                               ▼
                    ┌──────────────────────┐
                    │   Router/Supervisor   │  ← classifies intent
                    │       Agent           │
                    └──────┬───────────────┘
                           │ conditional edges
              ┌────────────┼────────────┬────────────┬──────────┐
              ▼            ▼            ▼            ▼          ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Booking  │ │Amenities │ │ Billing  │ │Complaints│ │ General  │
        │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │            │            │
             ▼            ▼            ▼            ▼            ▼
        ┌─────────────────────────────────────────────────────────────┐
        │              Tools Layer (mock PMS, RAG, billing DB)        │
        └─────────────────────────────────────────────────────────────┘

        ═══════════ Observability (Langfuse) ═══════════
        Every node traced: latency, tokens, cost, scores
```

## Project-Level Agents

### PM Agent (Project Manager)
- Orchestrates the overall guest interaction lifecycle
- Manages session state, conversation history, and handoffs between agents
- Tracks query resolution status and SLA compliance
- Decides when to escalate to human operators

### Review Agent
- Evaluates quality of responses before they reach the guest
- Checks for hallucinations, policy violations, tone issues
- Runs post-interaction quality assessments via LLM-as-judge
- Feeds evaluation scores back into Langfuse for monitoring

### Coding Agent (Template/Response Builder)
- Generates structured responses (confirmation emails, booking summaries)
- Builds dynamic response templates based on context
- Formats data from tools into guest-friendly messages

### DB Agent (Data Access)
- Manages all database and knowledge base interactions
- Handles ChromaDB vector store operations
- Interfaces with mock PMS/billing systems
- Ensures data consistency across agent interactions

### MCP Agent (Model Context Protocol)
- Manages tool registration and discovery via MCP protocol
- Provides standardized tool interfaces for all agents
- Handles tool versioning and capability negotiation
- Enables external system integration through MCP servers

## Observability: Monitoring Agent Performance

### What Gets Traced (Every Query)
| Metric | Where | How |
|--------|-------|-----|
| End-to-end latency | Langfuse trace | Trace duration from request to response |
| Intent classification | Router span | Input query → classified intent + confidence |
| Agent execution time | Agent span | Time spent in specialist agent |
| Tool calls | Tool spans (nested) | Each tool call with input/output/duration |
| RAG retrieval | Retrieval span | Query → retrieved chunks + relevance scores |
| Token usage | All LLM spans | Input/output tokens per call |
| Cost | Computed from tokens | Model-specific cost calculation |
| Errors | Span status + metadata | Exception type, message, stack trace |
| Quality scores | Evaluation spans | Helpfulness, accuracy, tone (1-5) |

### Diagnosing Issues
- **Slow responses**: Filter traces by latency > threshold → drill into spans → find bottleneck
- **Wrong routing**: Filter by low router confidence → review misclassified queries
- **Bad answers**: Filter by low evaluation scores → examine full trace → check RAG quality
- **High costs**: Group by intent → compare token usage → optimize prompts
- **Escalation spikes**: Filter complaint traces → identify common themes
