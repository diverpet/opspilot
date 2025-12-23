# OpsPilot - 生产环境故障排查智能体

[English](README.md) | 简体中文

OpsPilot 是一个基于 AI 的生产环境故障排查智能体，使用模型上下文协议（MCP）进行工具集成和上下文提供。它提供自动化的故障调查，并生成结构化的诊断报告，具有完整的可追溯性。

## 功能特性

- **MCP 架构**：所有工具调用都通过 MCP 进行，使智能体具有高度可扩展性
- **FSM 工作流**：结构化的调查流程：接收 → 澄清 → 调查 → 假设 → 验证 → 建议 → 报告
- **Schema 验证**：所有 LLM 输出都使用 Pydantic 进行验证，具有自动重试和降级机制
- **可观测性**：以 JSONL 格式记录所有 LLM 和 MCP 工具调用的完整追踪
- **双 LLM 支持**：生产环境使用 OpenAI，离线测试/演示使用 DummyLLM

## 架构

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

## 安装

```bash
# 克隆仓库
git clone https://github.com/diverpet/opspilot.git
cd opspilot

# 安装依赖
pip install -e .
# 或者
pip install -r requirements.txt
```

## 使用方法

### 启动 MCP 服务器（独立运行）

```bash
python -m opspilot_mcp.server --stdio
```

### 运行智能体

```bash
# 使用 DummyLLM（默认，无需 API 密钥）
python -m opspilot.main \
  --service api-gateway \
  --alert "高延迟告警：P99 > 2000ms" \
  --time-range 30m \
  --mcp-stdio "python -m opspilot_mcp.server --stdio"

# 使用 OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=gpt-4o-mini  # 可选

python -m opspilot.main \
  --service api-gateway \
  --alert "高延迟告警：P99 > 2000ms" \
  --time-range 30m \
  --mcp-stdio "python -m opspilot_mcp.server --stdio"
```

### 运行测试

```bash
python -m tests.run
```

## MCP 工具

MCP 服务器提供以下工具：

| 工具 | 描述 |
|------|-------------|
| `log_search` | 搜索服务日志并进行查询过滤 |
| `metric_query` | 查询时间序列指标（延迟、错误率、CPU 等） |
| `runbook_lookup` | 根据症状查找相关 Runbook |
| `change_history` | 获取最近的部署/变更历史 |
| `ticket_create` | 创建故障工单 |

## MCP 资源

| 资源 | 描述 |
|----------|-------------|
| `runbooks://index` | 列出所有可用的 Runbook |
| `runbooks://{name}` | 获取特定 Runbook 的内容 |

## 添加新的 MCP 工具

要添加新工具，您只需修改 MCP 服务器：

1. 在 `src/opspilot_mcp/tools/` 中创建工具实现：

```python
# src/opspilot_mcp/tools/my_new_tool.py
from ..schemas import MyToolInput, MyToolOutput

def my_new_tool(param1: str, param2: int) -> dict:
    # 验证输入
    input_data = MyToolInput(param1=param1, param2=param2)
    
    # 执行逻辑
    result = {...}
    
    # 验证输出
    output = MyToolOutput(**result)
    return output.model_dump()
```

2. 在 `src/opspilot_mcp/server.py` 中注册工具：

```python
# 添加到 list_tools()
Tool(
    name="my_new_tool",
    description="工具描述",
    inputSchema={...}
)

# 添加到 call_tool()
elif name == "my_new_tool":
    result = my_new_tool(arguments["param1"], arguments["param2"])
```

**智能体代码无需修改！** 智能体通过 MCP 自动发现工具。

## 输出产物

### 报告（Markdown）

```markdown
# 故障报告：API 网关高延迟

**服务：** api-gateway
**生成时间：** 2024-01-15T10:35:00
**置信度：** 85%

## 根因分析

数据库连接池耗尽，由于部署后流量激增导致。

## 证据链

1. **log_search**：检测到从 30 分钟前开始的连接超时错误
2. **metric_query**：延迟增加 5 倍，错误率升至 5%
3. **change_history**：发现修改连接池配置的部署

## 即时行动

- [ ] 回滚到之前的稳定版本
- [ ] 增加连接池大小
- [ ] 监控错误率
```

### 追踪日志（JSONL）

```json
{"ts": "2024-01-15T10:30:00", "event_type": "state", "name": "intake -> investigate", "input": "...", "output_summary": "", "ok": true, "latency_ms": 0}
{"ts": "2024-01-15T10:30:01", "event_type": "mcp_tool", "name": "log_search", "input": "{\"service\": \"api-gateway\"...}", "output_summary": "Found 15 log entries...", "ok": true, "latency_ms": 45}
{"ts": "2024-01-15T10:30:02", "event_type": "mcp_tool", "name": "metric_query", "input": "{\"service\": \"api-gateway\"...}", "output_summary": "High error rate: 5%...", "ok": true, "latency_ms": 32}
{"ts": "2024-01-15T10:30:05", "event_type": "llm", "name": "investigate", "input": "Analyze the investigation...", "output_summary": "{\"log_findings\":...", "ok": true, "latency_ms": 1500}
```

## 项目结构

```
opspilot/
├── src/
│   ├── opspilot/              # 智能体主机
│   │   ├── agent/
│   │   │   ├── fsm.py         # 状态机
│   │   │   ├── schemas.py     # Pydantic schemas
│   │   │   ├── runtime.py     # 智能体运行时
│   │   │   └── prompts.py     # LLM 提示词
│   │   ├── mcp_client/
│   │   │   └── client.py      # MCP 客户端封装
│   │   ├── observability/
│   │   │   └── tracer.py      # 追踪记录
│   │   ├── llm/
│   │   │   ├── base.py        # LLM 基础接口
│   │   │   ├── openai_llm.py  # OpenAI 提供者
│   │   │   └── dummy_llm.py   # 离线提供者
│   │   └── main.py            # CLI 入口点
│   │
│   └── opspilot_mcp/          # MCP 服务器
│       ├── server.py          # 服务器入口点
│       ├── tools/             # 工具实现
│       ├── resources/         # 资源处理器
│       ├── storage/           # 数据访问层
│       └── schemas.py         # 服务器 schemas
│
├── data/                       # 模拟数据
│   ├── logs/
│   ├── metrics/
│   └── changes/
├── runbooks/                   # Runbook 文档
├── artifacts/                  # 生成的报告/追踪
└── tests/
    ├── cases.yaml             # 测试场景
    └── run.py                 # 测试运行器
```

## 环境变量

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM 提供者（`openai` 或 `dummy`） | `dummy` |
| `OPENAI_API_KEY` | OpenAI API 密钥（使用 openai 时必需） | - |
| `OPENAI_MODEL` | OpenAI 模型名称 | `gpt-4o-mini` |

## 许可证

MIT
