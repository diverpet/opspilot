# OpsPilot - Production Incident Troubleshooting Agent

OpsPilot is an AI-powered production incident troubleshooting agent that uses the Model Context Protocol (MCP) for tool integration and context provision. It provides automated incident investigation with structured diagnostic reports and full traceability.

## Features

- **MCP Architecture**: All tool calls go through MCP, making the agent highly extensible
- **FSM Workflow**: Structured investigation flow: Intake → Clarify → Investigate → Hypothesis → Verify → Recommend → Report
- **Schema Validation**: All LLM outputs validated with Pydantic, with automatic retry and fallback
- **Observability**: Full trace of all LLM and MCP tool calls in JSONL format
- **Dual LLM Support**: OpenAI for production, DummyLLM for offline testing/demo

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Host (opspilot)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    FSM      │  │   LLM       │  │   Tracer    │             │
│  │  Workflow   │  │  Provider   │  │ (JSONL)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                           │                                      │
│                    MCP Client                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ stdio
┌───────────────────────────┴─────────────────────────────────────┐
│                    MCP Server (opspilot_mcp)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Tools     │  │  Resources  │  │   Storage   │             │
│  │ log_search  │  │  runbooks   │  │  data/*.    │             │
│  │ metric_query│  │             │  │             │             │
│  │ runbook_*   │  │             │  │             │             │
│  │ change_*    │  │             │  │             │             │
│  │ ticket_*    │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/diverpet/opspilot.git
cd opspilot

# Install dependencies
pip install -e .
# Or
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

The easiest way to use OpsPilot is through the web interface:

```bash
# Start the web server
python run_web.py

# Open your browser to http://localhost:5000
```

The web interface provides:
- **Interactive Form**: Easy-to-use form to submit incident investigations
- **Real-time Results**: View investigation progress and results
- **Investigation History**: Browse past investigations and their reports
- **Detailed Reports**: View full markdown reports and JSONL traces
- **Example Templates**: Quick-fill forms with example scenarios

![Web Interface](https://github.com/user-attachments/assets/ad529c30-f47d-4ae1-b135-c829c898c7c3)

Options:
```bash
python run_web.py --host 0.0.0.0 --port 5000 --debug
```

### Command Line Interface

For automation or scripting, use the CLI:

```bash
# Using DummyLLM (default, no API key needed)
python -m opspilot.main \
  --service api-gateway \
  --alert "High latency alert: P99 > 2000ms" \
  --time-range 30m \
  --mcp-stdio "python -m opspilot_mcp.server --stdio"

# Using OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=gpt-4o-mini  # optional

python -m opspilot.main \
  --service api-gateway \
  --alert "High latency alert: P99 > 2000ms" \
  --time-range 30m \
  --mcp-stdio "python -m opspilot_mcp.server --stdio"
```

### Start MCP Server (standalone)

```bash
python -m opspilot_mcp.server --stdio
```

### Run Tests

```bash
python -m tests.run
```

## MCP Tools

The MCP server provides the following tools:

| Tool | Description |
|------|-------------|
| `log_search` | Search logs for a service with query filtering |
| `metric_query` | Query time-series metrics (latency, error_rate, cpu, etc.) |
| `runbook_lookup` | Find relevant runbooks based on symptoms |
| `change_history` | Get recent deployment/change history |
| `ticket_create` | Create incident tickets |

## MCP Resources

| Resource | Description |
|----------|-------------|
| `runbooks://index` | List all available runbooks |
| `runbooks://{name}` | Get content of a specific runbook |

## Adding a New MCP Tool

To add a new tool, you only need to modify the MCP server:

1. Create tool implementation in `src/opspilot_mcp/tools/`:

```python
# src/opspilot_mcp/tools/my_new_tool.py
from ..schemas import MyToolInput, MyToolOutput

def my_new_tool(param1: str, param2: int) -> dict:
    # Validate input
    input_data = MyToolInput(param1=param1, param2=param2)
    
    # Execute logic
    result = {...}
    
    # Validate output
    output = MyToolOutput(**result)
    return output.model_dump()
```

2. Register the tool in `src/opspilot_mcp/server.py`:

```python
# Add to list_tools()
Tool(
    name="my_new_tool",
    description="Description of the tool",
    inputSchema={...}
)

# Add to call_tool()
elif name == "my_new_tool":
    result = my_new_tool(arguments["param1"], arguments["param2"])
```

**No changes needed in the agent code!** The agent discovers tools via MCP.

## Output Artifacts

### Report (Markdown)

```markdown
# Incident Report: API Gateway High Latency

**Service:** api-gateway
**Generated:** 2024-01-15T10:35:00
**Confidence:** 85%

## Root Cause Analysis

Database connection pool exhaustion due to traffic surge post-deployment.

## Evidence Chain

1. **log_search**: Connection timeout errors detected starting 30 minutes ago
2. **metric_query**: Latency increased 5x, error rate elevated to 5%
3. **change_history**: Deployment with connection pool configuration change

## Immediate Actions

- [ ] Rollback to previous stable version
- [ ] Increase connection pool size
- [ ] Monitor error rates
```

### Trace (JSONL)

```json
{"ts": "2024-01-15T10:30:00", "event_type": "state", "name": "intake -> investigate", "input": "...", "output_summary": "", "ok": true, "latency_ms": 0}
{"ts": "2024-01-15T10:30:01", "event_type": "mcp_tool", "name": "log_search", "input": "{\"service\": \"api-gateway\"...}", "output_summary": "Found 15 log entries...", "ok": true, "latency_ms": 45}
{"ts": "2024-01-15T10:30:02", "event_type": "mcp_tool", "name": "metric_query", "input": "{\"service\": \"api-gateway\"...}", "output_summary": "High error rate: 5%...", "ok": true, "latency_ms": 32}
{"ts": "2024-01-15T10:30:05", "event_type": "llm", "name": "investigate", "input": "Analyze the investigation...", "output_summary": "{\"log_findings\":...", "ok": true, "latency_ms": 1500}
```

## Project Structure

```
opspilot/
├── src/
│   ├── opspilot/              # Agent Host
│   │   ├── agent/
│   │   │   ├── fsm.py         # State machine
│   │   │   ├── schemas.py     # Pydantic schemas
│   │   │   ├── runtime.py     # Agent runtime
│   │   │   └── prompts.py     # LLM prompts
│   │   ├── mcp_client/
│   │   │   └── client.py      # MCP client wrapper
│   │   ├── observability/
│   │   │   └── tracer.py      # Trace recording
│   │   ├── llm/
│   │   │   ├── base.py        # Base LLM interface
│   │   │   ├── openai_llm.py  # OpenAI provider
│   │   │   └── dummy_llm.py   # Offline provider
│   │   └── main.py            # CLI entry point
│   │
│   └── opspilot_mcp/          # MCP Server
│       ├── server.py          # Server entry point
│       ├── tools/             # Tool implementations
│       ├── resources/         # Resource handlers
│       ├── storage/           # Data access layer
│       └── schemas.py         # Server schemas
│
├── data/                       # Mock data
│   ├── logs/
│   ├── metrics/
│   └── changes/
├── runbooks/                   # Runbook documents
├── artifacts/                  # Generated reports/traces
└── tests/
    ├── cases.yaml             # Test scenarios
    └── run.py                 # Test runner
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (`openai` or `dummy`) | `dummy` |
| `OPENAI_API_KEY` | OpenAI API key (required if using openai) | - |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |

## License

MIT
