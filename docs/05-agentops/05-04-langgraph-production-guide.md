# 5.4 Making OSS LangGraph Production-Grade

## Overview

LangGraph is the leading open-source framework for building stateful, multi-actor agentic AI applications. While its graph-based orchestration model is powerful for development, running LangGraph reliably in production requires careful attention to deployment architecture, security, observability, concurrency, cost, and ongoing maintenance.

This guide covers the key considerations and proven patterns for making open-source LangGraph production-ready across six critical dimensions:

1. **Deployment for Scale & Performance**
2. **Security**
3. **Observability**
4. **Concurrency Control**
5. **Cost Management**
6. **Support & Maintenance**

> **Note:** This guide focuses on the **open-source (OSS) LangGraph library** and self-managed deployment options. LangGraph Platform (the managed commercial offering from LangChain Inc.) addresses many of these concerns out of the box but introduces vendor dependency and cost. The patterns below enable enterprises to achieve production-grade quality while retaining full control.

---

## 1. Deployment for Scale & Performance

### 1.1 Architecture Patterns

#### Stateless Executor + External State Store

The foundational pattern for scaling LangGraph is to separate the **graph execution runtime** from **state persistence**. Graph executors remain stateless and horizontally scalable, while checkpointed state lives in a shared external store.

```
                    ┌────────────────────┐
                    │   Load Balancer    │
                    └────────┬───────────┘
               ┌─────────────┼─────────────┐
               ▼             ▼             ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │ LangGraph  │ │ LangGraph  │ │ LangGraph  │
        │ Executor 1 │ │ Executor 2 │ │ Executor N │
        └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                  ┌─────────────────────┐
                  │   Checkpoint Store  │
                  │  (PostgreSQL/Redis) │
                  └─────────────────────┘
```

**Implementation:**
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# External checkpoint store for durable state
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@db-host:5432/langgraph_checkpoints"
)

# Compile graph with external checkpointer
app = graph.compile(checkpointer=checkpointer)

# Each invocation is stateless — state is loaded/saved via checkpointer
result = app.invoke(
    {"messages": [{"role": "user", "content": "Analyze Q4 revenue"}]},
    config={"configurable": {"thread_id": "session-abc-123"}}
)
```

#### Containerized Deployment (Kubernetes)

Package LangGraph executors as container images and deploy on Kubernetes for auto-scaling, rolling updates, and self-healing.

```yaml
# Kubernetes Deployment for LangGraph Executor
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph-executor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: langgraph-executor
  template:
    metadata:
      labels:
        app: langgraph-executor
    spec:
      containers:
        - name: executor
          image: myregistry/langgraph-executor:v1.2.0
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          env:
            - name: CHECKPOINT_DB_URL
              valueFrom:
                secretKeyRef:
                  name: langgraph-secrets
                  key: checkpoint-db-url
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 30
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: langgraph-executor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: langgraph-executor
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: active_graph_runs
        target:
          type: AverageValue
          averageValue: "10"
```

### 1.2 Performance Optimization

#### Checkpoint Store Selection

| Store | Best For | Latency | Durability | Scalability |
|---|---|---|---|---|
| **PostgreSQL** (`PostgresSaver`) | Production workloads | ~5–10ms | ✅ Strong | ✅ Vertical + read replicas |
| **Redis** | Low-latency, ephemeral state | ~1ms | ⚠️ Configurable (AOF/RDB) | ✅ Cluster mode |
| **SQLite** (`SqliteSaver`) | Development/testing only | ~1ms (local) | ⚠️ Single-node | ❌ Not distributed |
| **MongoDB** | Document-heavy state | ~5ms | ✅ Strong | ✅ Sharding |

**PostgreSQL Tuning for Checkpointing:**
```sql
-- Optimize for checkpoint write patterns
ALTER TABLE checkpoints SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE checkpoints SET (autovacuum_analyze_scale_factor = 0.02);

-- Create indexes for fast thread-based lookups
CREATE INDEX idx_checkpoints_thread ON checkpoints (thread_id, checkpoint_id DESC);

-- Connection pooling (use PgBouncer or built-in pool)
-- Recommended: transaction-level pooling with pool_size = 2 × executor_count
```

#### Graph Compilation Caching

Compile graphs once at startup and reuse across requests to avoid repeated compilation overhead:

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def get_compiled_graph():
    """Compile graph once, reuse across all requests."""
    graph = build_my_graph()
    return graph.compile(checkpointer=get_checkpointer())

# In request handler
app = get_compiled_graph()
result = app.invoke(inputs, config=config)
```

#### Async Execution

Use LangGraph's async API (`ainvoke`, `astream`) for I/O-bound workloads to maximize throughput:

```python
import asyncio
from fastapi import FastAPI

api = FastAPI()
app = get_compiled_graph()

@api.post("/run")
async def run_graph(request: GraphRequest):
    """Async endpoint for high-throughput graph execution."""
    result = await app.ainvoke(
        {"messages": request.messages},
        config={"configurable": {"thread_id": request.thread_id}}
    )
    return result
```

#### Background Task Queues

For long-running agent workflows, decouple request handling from execution using a task queue:

```python
from celery import Celery

celery_app = Celery("langgraph_tasks", broker="redis://redis:6379/0")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_agent_workflow(self, thread_id: str, inputs: dict):
    """Execute a long-running graph workflow in the background."""
    try:
        app = get_compiled_graph()
        result = app.invoke(
            inputs,
            config={"configurable": {"thread_id": thread_id}}
        )
        return result
    except Exception as exc:
        self.retry(exc=exc)
```

### 1.3 Streaming for Responsiveness

Enable token-level streaming to provide responsive UX for agentic workflows:

```python
@api.post("/stream")
async def stream_graph(request: GraphRequest):
    """Stream graph execution events for responsive UX."""
    app = get_compiled_graph()

    async def event_generator():
        async for event in app.astream_events(
            {"messages": request.messages},
            config={"configurable": {"thread_id": request.thread_id}},
            version="v2",
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 2. Security

### 2.1 Authentication & Authorization

#### API Gateway Integration

Wrap LangGraph endpoints behind an API gateway or reverse proxy that handles authentication:

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from API gateway or direct client."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            options={"verify_signature": True},
            key=PUBLIC_KEY,
            algorithms=["RS256"],
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@api.post("/run")
async def run_graph(request: GraphRequest, user=Depends(verify_token)):
    """Authenticated graph execution endpoint."""
    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "user_id": user["sub"],          # Track who started the run
        }
    }
    result = await app.ainvoke(request.inputs, config=config)
    return result
```

#### Thread-Level Access Control

Enforce per-user isolation so that users can only access their own threads and conversation histories:

```python
async def authorize_thread_access(thread_id: str, user_id: str):
    """Ensure users can only access their own threads."""
    thread_owner = await get_thread_owner(thread_id)
    if thread_owner and thread_owner != user_id:
        raise HTTPException(status_code=403, detail="Access denied to thread")
```

#### Tool-Level Permissions

Control which tools each user or role can invoke within a graph execution:

```python
from typing import List

def create_graph_with_permissions(allowed_tools: List[str]):
    """Build graph with tool access scoped to user permissions."""
    available_tools = {
        "web_search": web_search_tool,
        "database_query": db_query_tool,
        "send_email": send_email_tool,
        "file_write": file_write_tool,
    }
    # Only include tools the user is allowed to use
    user_tools = [available_tools[t] for t in allowed_tools if t in available_tools]
    return create_react_agent(model, user_tools)
```

### 2.2 Secrets Management

Never embed secrets in code or environment variables. Use a secrets manager:

```python
import boto3
from functools import lru_cache

@lru_cache()
def get_secret(secret_name: str) -> str:
    """Retrieve secrets from AWS Secrets Manager (or Vault, GCP Secret Manager)."""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]

# Usage
checkpointer = PostgresSaver.from_conn_string(
    get_secret("langgraph/checkpoint-db-url")
)
```

### 2.3 Input Validation & Guardrails

Validate and sanitize all inputs before they reach the LLM or tools:

```python
from pydantic import BaseModel, Field, validator

class GraphInput(BaseModel):
    messages: list = Field(..., max_length=50)  # Limit conversation length
    thread_id: str = Field(..., pattern=r"^[a-zA-Z0-9\-]{1,64}$")

    @validator("messages", each_item=True)
    def validate_message_content(cls, msg):
        if len(msg.get("content", "")) > 10000:
            raise ValueError("Message content exceeds maximum length")
        return msg

def input_guardrail(state: dict) -> dict:
    """Pre-execution guardrail node to filter harmful or policy-violating inputs."""
    last_message = state["messages"][-1]["content"]
    if contains_pii(last_message):
        return {
            "messages": state["messages"] + [
                {"role": "assistant", "content": "I cannot process requests containing PII."}
            ],
            "__end__": True,
        }
    return state
```

### 2.4 Network Security

- **mTLS** between executors and checkpoint stores
- **Network policies** in Kubernetes to restrict pod-to-pod communication
- **Private subnets** for checkpoint databases — no public internet exposure
- **Egress control** to whitelist only required external APIs (LLM providers, tool endpoints)

```yaml
# Kubernetes NetworkPolicy — restrict executor egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: langgraph-executor-egress
spec:
  podSelector:
    matchLabels:
      app: langgraph-executor
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: checkpoint-db
      ports:
        - port: 5432
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - port: 443  # HTTPS only for LLM API calls
```

---

## 3. Observability

### 3.1 Structured Logging

Emit structured logs at every node execution for traceability:

```python
import structlog

logger = structlog.get_logger()

def create_observable_node(node_name: str, node_fn):
    """Wrap a graph node with structured logging."""
    async def wrapper(state: dict, config: dict) -> dict:
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        logger.info(
            "node_started",
            node=node_name,
            thread_id=thread_id,
            state_keys=list(state.keys()),
        )
        try:
            result = await node_fn(state, config)
            logger.info(
                "node_completed",
                node=node_name,
                thread_id=thread_id,
            )
            return result
        except Exception as e:
            logger.error(
                "node_failed",
                node=node_name,
                thread_id=thread_id,
                error=str(e),
            )
            raise
    return wrapper
```

### 3.2 Distributed Tracing

Integrate with OpenTelemetry for end-to-end distributed tracing across graph nodes, LLM calls, and tool invocations:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize OpenTelemetry
provider = TracerProvider()
provider.add_span_processor(BatchSpanExporter(OTLPSpanExporter(endpoint="otel-collector:4317")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("langgraph-app")

def traced_node(node_name: str, node_fn):
    """Wrap a graph node with OpenTelemetry tracing."""
    async def wrapper(state: dict, config: dict) -> dict:
        with tracer.start_as_current_span(
            f"graph.node.{node_name}",
            attributes={
                "langgraph.node": node_name,
                "langgraph.thread_id": config.get("configurable", {}).get("thread_id", ""),
            },
        ) as span:
            result = await node_fn(state, config)
            span.set_attribute("langgraph.node.success", True)
            return result
    return wrapper
```

### 3.3 Metrics & Dashboards

Export key metrics via Prometheus for Grafana dashboards:

```python
from prometheus_client import Counter, Histogram, Gauge

# Core metrics
graph_runs_total = Counter(
    "langgraph_graph_runs_total",
    "Total graph executions",
    ["graph_name", "status"],
)
node_duration_seconds = Histogram(
    "langgraph_node_duration_seconds",
    "Time spent in each node",
    ["graph_name", "node_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)
active_runs = Gauge(
    "langgraph_active_runs",
    "Number of currently active graph runs",
)
llm_tokens_total = Counter(
    "langgraph_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "direction"],  # direction: input/output
)
```

**Key Metrics to Monitor:**

| Metric | Description | Alert Threshold |
|---|---|---|
| `langgraph_graph_runs_total` | Total runs by status (success/failure) | Error rate > 5% |
| `langgraph_node_duration_seconds` | Per-node execution latency | p99 > 30s |
| `langgraph_active_runs` | Concurrent graph executions | > 80% of capacity |
| `langgraph_llm_tokens_total` | Token consumption by model | Daily budget exceeded |
| `langgraph_checkpoint_ops_total` | Checkpoint read/write operations | Error rate > 1% |
| `langgraph_tool_calls_total` | Tool invocations by tool name | Failure rate > 10% |

### 3.4 LangSmith Integration (Optional)

LangSmith provides purpose-built observability for LangChain/LangGraph applications. If acceptable to your security posture, it offers deep tracing without custom instrumentation:

```python
import os

# Enable LangSmith tracing (sends data to LangSmith cloud)
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = get_secret("langsmith/api-key")
os.environ["LANGSMITH_PROJECT"] = "production-agents"
```

> **Trade-off:** LangSmith provides excellent agent-specific observability but sends trace data to an external service. For regulated environments, prefer self-hosted OpenTelemetry pipelines.

---

## 4. Concurrency Control

### 4.1 Thread-Level Locking

Prevent race conditions when multiple requests target the same conversation thread:

```python
import asyncio
from collections import defaultdict

class ThreadLockManager:
    """Manages per-thread locks to prevent concurrent writes to the same thread."""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def run_with_lock(self, thread_id: str, coro):
        """Execute a coroutine while holding the thread lock."""
        async with self._locks[thread_id]:
            return await coro

thread_locks = ThreadLockManager()

@api.post("/run")
async def run_graph(request: GraphRequest, user=Depends(verify_token)):
    async def _execute():
        return await app.ainvoke(
            request.inputs,
            config={"configurable": {"thread_id": request.thread_id}},
        )
    return await thread_locks.run_with_lock(request.thread_id, _execute())
```

### 4.2 Distributed Locking

For multi-instance deployments, use Redis-based distributed locks:

```python
import redis.asyncio as redis
from contextlib import asynccontextmanager

redis_client = redis.from_url("redis://redis:6379/1")

@asynccontextmanager
async def distributed_thread_lock(thread_id: str, timeout: int = 300):
    """Distributed lock to ensure single-writer per thread across instances."""
    lock_key = f"langgraph:lock:{thread_id}"
    lock = redis_client.lock(lock_key, timeout=timeout, blocking_timeout=30)
    acquired = await lock.acquire()
    if not acquired:
        raise HTTPException(status_code=409, detail="Thread is currently being processed")
    try:
        yield
    finally:
        await lock.release()

@api.post("/run")
async def run_graph(request: GraphRequest):
    async with distributed_thread_lock(request.thread_id):
        result = await app.ainvoke(
            request.inputs,
            config={"configurable": {"thread_id": request.thread_id}},
        )
    return result
```

### 4.3 Rate Limiting

Protect against abuse and ensure fair resource allocation:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@api.post("/run")
@limiter.limit("10/minute")       # Per-IP rate limit
async def run_graph(request: GraphRequest, user=Depends(verify_token)):
    ...

@api.post("/stream")
@limiter.limit("5/minute")        # Streaming is more resource-intensive
async def stream_graph(request: GraphRequest, user=Depends(verify_token)):
    ...
```

### 4.4 Execution Timeouts

Prevent runaway agent loops from consuming resources indefinitely:

```python
import asyncio

async def run_with_timeout(app, inputs, config, timeout_seconds=300):
    """Execute graph with a hard timeout to prevent infinite loops."""
    try:
        result = await asyncio.wait_for(
            app.ainvoke(inputs, config=config),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("graph_timeout", thread_id=config["configurable"]["thread_id"])
        raise HTTPException(status_code=504, detail="Agent execution timed out")
```

### 4.5 Recursion Limits

LangGraph's built-in recursion limit prevents infinite cycles in graph execution:

```python
# Set recursion limit at compile time or invocation time
app = graph.compile(checkpointer=checkpointer)

result = app.invoke(
    inputs,
    config={
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,  # Maximum number of supersteps
    },
)
```

---

## 5. Cost Management

### 5.1 Token Usage Tracking

Track and attribute LLM token consumption per user, team, or workflow:

```python
from langchain_core.callbacks import BaseCallbackHandler

class TokenTracker(BaseCallbackHandler):
    """Track LLM token usage for cost attribution."""

    def __init__(self, user_id: str, graph_name: str):
        self.user_id = user_id
        self.graph_name = graph_name

    def on_llm_end(self, response, **kwargs):
        usage = response.llm_output.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Record to metrics system
        llm_tokens_total.labels(
            model=response.llm_output.get("model_name", "unknown"),
            direction="input",
        ).inc(input_tokens)
        llm_tokens_total.labels(
            model=response.llm_output.get("model_name", "unknown"),
            direction="output",
        ).inc(output_tokens)

        # Store for billing/attribution
        record_usage(
            user_id=self.user_id,
            graph_name=self.graph_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

# Usage
result = await app.ainvoke(
    inputs,
    config={
        "configurable": {"thread_id": thread_id},
        "callbacks": [TokenTracker(user_id="user-123", graph_name="analyst")],
    },
)
```

### 5.2 Budget Guardrails

Enforce per-user or per-team token budgets to prevent cost overruns:

```python
class BudgetGuardrail:
    """Enforce token budget limits per user/team."""

    def __init__(self, daily_limit: int = 100_000):
        self.daily_limit = daily_limit

    async def check_budget(self, user_id: str) -> bool:
        today_usage = await get_daily_token_usage(user_id)
        return today_usage < self.daily_limit

    async def enforce(self, user_id: str):
        if not await self.check_budget(user_id):
            raise HTTPException(
                status_code=429,
                detail="Daily token budget exceeded. Resets at midnight UTC.",
            )

budget = BudgetGuardrail(daily_limit=100_000)

@api.post("/run")
async def run_graph(request: GraphRequest, user=Depends(verify_token)):
    await budget.enforce(user["sub"])
    ...
```

### 5.3 Model Routing for Cost Optimization

Route simpler tasks to cheaper models and reserve expensive models for complex reasoning:

```python
from langchain_openai import ChatOpenAI

# Define model tiers
MODELS = {
    "fast": ChatOpenAI(model="gpt-4o-mini", temperature=0),
    "standard": ChatOpenAI(model="gpt-4o", temperature=0),
    "reasoning": ChatOpenAI(model="o3-mini", temperature=1),
}

def select_model(task_complexity: str):
    """Route to cost-appropriate model based on task complexity."""
    return MODELS.get(task_complexity, MODELS["standard"])

def router_node(state: dict) -> dict:
    """Classify task complexity and select appropriate model."""
    complexity = classify_complexity(state["messages"][-1]["content"])
    state["selected_model"] = complexity
    return state
```

### 5.4 Checkpoint Storage Optimization

Reduce storage costs by managing checkpoint lifecycle:

```python
async def cleanup_old_checkpoints(retention_days: int = 30):
    """Remove checkpoints older than retention period."""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    await db.execute(
        "DELETE FROM checkpoints WHERE created_at < $1",
        cutoff,
    )

async def compact_thread_checkpoints(thread_id: str, keep_last: int = 10):
    """Keep only the most recent N checkpoints per thread."""
    await db.execute(
        """
        DELETE FROM checkpoints
        WHERE thread_id = $1
        AND checkpoint_id NOT IN (
            SELECT checkpoint_id FROM checkpoints
            WHERE thread_id = $1
            ORDER BY checkpoint_id DESC
            LIMIT $2
        )
        """,
        thread_id,
        keep_last,
    )
```

### 5.5 Infrastructure Cost Controls

| Strategy | Implementation | Typical Savings |
|---|---|---|
| **Right-size executor pods** | Profile actual CPU/memory usage; adjust resource requests | 20–40% |
| **Spot/preemptible instances** | Use for non-critical or retryable workloads | 60–80% compute cost |
| **Scale-to-zero** | Use KEDA or Knative to scale executors to zero during idle periods | Variable (off-hours) |
| **Connection pooling** | Use PgBouncer for checkpoint DB connections | Fewer DB instances needed |
| **Caching LLM responses** | Cache deterministic tool calls and repeated queries | 10–30% token cost |

---

## 6. Support & Maintenance

### 6.1 Dependency Management

Pin LangGraph and LangChain dependencies to avoid breaking changes:

```txt
# requirements.txt — pin to exact versions for reproducibility
langgraph==0.4.1
langgraph-checkpoint-postgres==2.0.18
langchain-core==0.3.51
langchain-openai==0.3.18
```

**Upgrade Strategy:**
1. Track releases via the [LangGraph GitHub releases](https://github.com/langchain-ai/langgraph/releases) and changelog
2. Test upgrades in a staging environment with integration tests before promoting
3. Use automated dependency scanning (e.g., Dependabot, Renovate) for security patches
4. Pin major and minor versions; allow patch updates for security fixes

### 6.2 Integration & Regression Testing

Build automated tests around graph behavior to catch regressions early:

```python
import pytest

@pytest.mark.asyncio
async def test_graph_happy_path():
    """Test the primary workflow completes successfully."""
    app = get_compiled_graph()
    result = await app.ainvoke(
        {"messages": [{"role": "user", "content": "Summarize sales for Q4"}]},
        config={"configurable": {"thread_id": "test-thread-001"}},
    )
    assert "messages" in result
    assert len(result["messages"]) > 1

@pytest.mark.asyncio
async def test_graph_respects_recursion_limit():
    """Verify the graph terminates within recursion limits."""
    app = get_compiled_graph()
    with pytest.raises(Exception, match="Recursion"):
        await app.ainvoke(
            {"messages": [{"role": "user", "content": "Loop forever"}]},
            config={
                "configurable": {"thread_id": "test-thread-002"},
                "recursion_limit": 3,
            },
        )

@pytest.mark.asyncio
async def test_checkpoint_persistence():
    """Verify state is persisted and recoverable across invocations."""
    app = get_compiled_graph()
    thread_id = "test-thread-003"
    config = {"configurable": {"thread_id": thread_id}}

    # First invocation
    await app.ainvoke(
        {"messages": [{"role": "user", "content": "Start analysis"}]},
        config=config,
    )

    # Second invocation on same thread should have prior state
    state = await app.aget_state(config)
    assert len(state.values["messages"]) > 0
```

### 6.3 CI/CD Pipeline

Automate build, test, and deployment for LangGraph applications:

```yaml
# .github/workflows/langgraph-ci.yml
name: LangGraph CI/CD

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: langgraph_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v --tb=short
        env:
          CHECKPOINT_DB_URL: postgresql://test:test@localhost:5432/langgraph_test

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push container
        run: |
          docker build -t myregistry/langgraph-executor:${{ github.sha }} .
          docker push myregistry/langgraph-executor:${{ github.sha }}
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/langgraph-executor \
            executor=myregistry/langgraph-executor:${{ github.sha }}
```

### 6.4 Health Checks & Self-Healing

Implement health and readiness checks for reliable operations:

```python
from fastapi import FastAPI

api = FastAPI()

@api.get("/health")
async def health_check():
    """Liveness probe — is the process running?"""
    return {"status": "healthy"}

@api.get("/ready")
async def readiness_check():
    """Readiness probe — can the executor accept work?"""
    checks = {
        "checkpoint_db": await check_db_connection(),
        "llm_api": await check_llm_connectivity(),
    }
    all_ok = all(checks.values())
    return {"ready": all_ok, "checks": checks}

async def check_db_connection() -> bool:
    try:
        await db.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_llm_connectivity() -> bool:
    try:
        # Lightweight ping to LLM provider
        await model.ainvoke([{"role": "user", "content": "ping"}])
        return True
    except Exception:
        return False
```

### 6.5 Versioning & Rollback

Maintain versioned graph definitions for safe rollbacks:

```python
# Version your graph definitions
GRAPH_REGISTRY = {
    "analyst_v1": build_analyst_graph_v1,
    "analyst_v2": build_analyst_graph_v2,
}

def get_graph(name: str, version: str = "latest"):
    """Retrieve a specific graph version for canary or rollback scenarios."""
    key = f"{name}_{version}" if version != "latest" else max(
        k for k in GRAPH_REGISTRY if k.startswith(name)
    )
    return GRAPH_REGISTRY[key]()
```

### 6.6 Operational Runbook Summary

| Scenario | Action |
|---|---|
| **High error rate** | Check LLM API status, review error logs, verify checkpoint DB connectivity |
| **Latency spike** | Check checkpoint store latency, LLM response times, pod resource utilization |
| **OOM kills** | Increase memory limits, profile state size, enable checkpoint compaction |
| **Checkpoint DB full** | Run checkpoint cleanup job, increase storage, review retention policy |
| **Dependency CVE** | Patch immediately, test in staging, deploy with rolling update |
| **Graph behavior regression** | Roll back graph version, run regression tests, investigate root cause |
| **Cost spike** | Check token usage dashboards, review budget guardrails, audit model routing |

---

## Decision Matrix: Self-Managed OSS vs. LangGraph Platform

| Dimension | Self-Managed OSS | LangGraph Platform (Commercial) |
|---|---|---|
| **Deployment** | You manage K8s, containers, scaling | Managed auto-scaling infrastructure |
| **Checkpointing** | PostgreSQL/Redis — you manage | Built-in managed persistence |
| **Authentication** | Build with API gateway / custom | Built-in API key + OAuth |
| **Observability** | OpenTelemetry + Prometheus + Grafana | LangSmith integrated tracing |
| **Concurrency** | Implement distributed locking | Built-in thread-level queuing |
| **Cost** | Infrastructure only — no license fee | Per-usage pricing + infrastructure |
| **Support** | Community (GitHub Issues, Discord) | Commercial support + SLAs |
| **Control** | Full control over stack | Vendor-managed black box |
| **Best For** | Teams with platform engineering capacity | Teams wanting managed experience |

---

## Key Takeaways

1. **Separate compute from state** — Use external checkpoint stores (PostgreSQL/Redis) and stateless executors for horizontal scaling.
2. **Secure every layer** — Authenticate API endpoints, authorize thread access, manage secrets externally, and enforce network policies.
3. **Instrument everything** — Structured logging, OpenTelemetry tracing, and Prometheus metrics provide the visibility needed for production operations.
4. **Control concurrency** — Thread-level locking (local or distributed) and rate limiting prevent race conditions and resource abuse.
5. **Track and cap costs** — Token usage tracking, budget guardrails, and model routing ensure cost predictability.
6. **Automate operations** — CI/CD pipelines, health checks, dependency management, and operational runbooks reduce toil and increase reliability.

---

**Next:** [5.5 Feedback & Learning](../05-agentops.md#54-feedback--learning) | [Back to TOC](../../README.md)
