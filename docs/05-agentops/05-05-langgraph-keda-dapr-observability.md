# 5.5 Scaling LangGraph with KEDA & Dapr on Kubernetes + Unified Observability

## Overview

Deploying LangGraph-based agentic AI solutions at enterprise scale requires more than just containerization. Two CNCF projects — **KEDA** (Kubernetes Event-Driven Autoscaling) and **Dapr** (Distributed Application Runtime) — fill critical gaps in the Kubernetes-native deployment story for LangGraph, providing event-driven scaling, distributed state management, and inter-service communication without custom infrastructure code.

Equally important is a **unified observability strategy** that captures data across four dimensions — agent-level tracing, user-level tracking, hardware/infrastructure metrics, and application logs — and aggregates them into a single pane of glass with correlation, dashboarding, and actionable insights.

This guide covers:

1. [KEDA in the LangGraph Deployment Architecture](#1-keda-in-the-langgraph-deployment-architecture)
2. [Dapr in the LangGraph Deployment Architecture](#2-dapr-in-the-langgraph-deployment-architecture)
3. [Combined Architecture: LangGraph + KEDA + Dapr on Kubernetes](#3-combined-architecture-langgraph--keda--dapr-on-kubernetes)
4. [Monitoring Dimension 1: Agent-Level Logging & Tracing](#4-monitoring-dimension-1-agent-level-logging--tracing)
5. [Monitoring Dimension 2: User-Level Tracking](#5-monitoring-dimension-2-user-level-tracking)
6. [Monitoring Dimension 3: Hardware & Infrastructure Metrics](#6-monitoring-dimension-3-hardware--infrastructure-metrics)
7. [Monitoring Dimension 4: Application Logs](#7-monitoring-dimension-4-application-logs)
8. [Centralized Observability: Aggregation, Correlation & Dashboarding](#8-centralized-observability-aggregation-correlation--dashboarding)

---

## 1. KEDA in the LangGraph Deployment Architecture

### What Is KEDA?

**KEDA (Kubernetes Event-Driven Autoscaling)** is a CNCF graduated project that extends Kubernetes with event-driven autoscaling. Unlike standard Kubernetes HPA (which scales on CPU/memory), KEDA scales workloads based on **external event sources** — message queue depth, HTTP request rate, database query backlog, cron schedules, or custom metrics.

### Why KEDA Matters for LangGraph

LangGraph workloads are inherently **bursty and event-driven** — a user request triggers a graph run that may invoke multiple LLM calls, tool executions, and state transitions. Standard CPU-based autoscaling reacts too slowly and cannot **scale to zero** during idle periods. KEDA solves these problems:

| Challenge | Standard K8s HPA | KEDA |
|---|---|---|
| Scale on queue depth (pending agent tasks) | ❌ | ✅ ScaledObject with queue trigger |
| Scale to zero when idle | ❌ (min 1 replica) | ✅ Native scale-to-zero |
| Scale on custom metrics (active graph runs) | ⚠️ Custom metrics adapter | ✅ Built-in Prometheus scaler |
| Cron-based pre-scaling (business hours) | ❌ | ✅ Cron trigger |
| Scale on HTTP request rate | ❌ | ✅ HTTP add-on |
| React to Kafka/Redis/RabbitMQ events | ❌ | ✅ 60+ built-in scalers |

### KEDA's Position in the Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                              │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     KEDA Operator                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐   │  │
│  │  │ Metrics      │  │ ScaledObject │  │ ScaledJob         │   │  │
│  │  │ Adapter      │  │ Controller   │  │ Controller        │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘   │  │
│  └─────────┼─────────────────┼───────────────────┼──────────────┘  │
│            │                 │                   │                  │
│            ▼                 ▼                   ▼                  │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │
│  │ Prometheus   │  │ LangGraph       │  │ LangGraph           │   │
│  │ (metrics     │  │ Executor        │  │ Background Worker   │   │
│  │  source)     │  │ Deployment      │  │ Jobs                │   │
│  └──────────────┘  │ (ScaledObject)  │  │ (ScaledJob)         │   │
│                    └────────┬────────┘  └──────────┬──────────┘   │
│            ┌───────────────┐│┌──────────────────┐  │              │
│            │ Redis / Kafka ││ │ PostgreSQL       │  │              │
│            │ (task queue)  │││ (checkpoints)     │  │              │
│            └───────────────┘│└──────────────────┘  │              │
│                             │                      │              │
│  Event Sources:             │                      │              │
│  • Redis queue depth ───────┘                      │              │
│  • Prometheus metrics ─────────────────────────────┘              │
│  • Cron schedules                                                 │
│  • HTTP traffic rate                                              │
└─────────────────────────────────────────────────────────────────────┘
```

KEDA sits **between the event sources and the Kubernetes scaling API**. It watches external signals (queue depth, metrics, schedules) and adjusts the replica count of LangGraph executor Deployments or creates Jobs for batch processing — all without custom scaling code.

### KEDA Configuration for LangGraph

#### Scale Executors on Task Queue Depth

```yaml
# ScaledObject: Scale LangGraph executors based on Redis queue depth
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: langgraph-executor-scaler
spec:
  scaleTargetRef:
    name: langgraph-executor          # Target Deployment
  minReplicaCount: 0                  # Scale to zero when idle
  maxReplicaCount: 50
  pollingInterval: 15                 # Check every 15 seconds
  cooldownPeriod: 120                 # Wait 2 min before scaling down
  triggers:
    # Scale based on pending tasks in Redis queue
    - type: redis
      metadata:
        address: redis.default.svc.cluster.local:6379
        listName: langgraph:task_queue
        listLength: "5"               # 1 replica per 5 pending tasks
        activationListLength: "1"     # Activate from zero at 1 task
    # Also scale based on active graph runs (Prometheus metric)
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        query: sum(langgraph_active_runs)
        threshold: "10"               # 1 replica per 10 active runs
```

#### Scale Background Workers with ScaledJob

```yaml
# ScaledJob: One-shot jobs for long-running agent workflows
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: langgraph-batch-worker
spec:
  jobTargetRef:
    template:
      spec:
        containers:
          - name: worker
            image: myregistry/langgraph-worker:latest
            env:
              - name: CHECKPOINT_DB_URL
                valueFrom:
                  secretKeyRef:
                    name: langgraph-secrets
                    key: checkpoint-db-url
        restartPolicy: OnFailure
  pollingInterval: 10
  maxReplicaCount: 100
  successfulJobsHistoryLimit: 10
  failedJobsHistoryLimit: 5
  triggers:
    - type: redis
      metadata:
        address: redis.default.svc.cluster.local:6379
        listName: langgraph:batch_queue
        listLength: "1"              # 1 job per pending batch task
```

#### Cron-Based Pre-Scaling for Business Hours

```yaml
# Scale up proactively during business hours
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: langgraph-cron-scaler
spec:
  scaleTargetRef:
    name: langgraph-executor
  triggers:
    - type: cron
      metadata:
        timezone: America/New_York
        start: 0 8 * * 1-5           # Mon–Fri 8 AM
        end: 0 20 * * 1-5            # Mon–Fri 8 PM
        desiredReplicas: "5"          # Pre-warm 5 replicas
```

---

## 2. Dapr in the LangGraph Deployment Architecture

### What Is Dapr?

**Dapr (Distributed Application Runtime)** is a CNCF graduated project that provides portable, event-driven runtime building blocks for distributed applications. It runs as a **sidecar** alongside each application container, offering APIs for state management, pub/sub messaging, service invocation, secrets, bindings, and actors — all with pluggable backends.

### Why Dapr Matters for LangGraph

LangGraph executors need several distributed capabilities that are difficult to build and maintain: reliable state persistence, inter-agent messaging, secrets access, and service-to-service communication. Dapr provides all of these **as standardized APIs** without locking into specific infrastructure.

| LangGraph Need | Without Dapr | With Dapr |
|---|---|---|
| **State persistence** | Direct PostgreSQL/Redis client in app code | Dapr State API — swap backends without code changes |
| **Inter-agent messaging** | Custom Kafka/Redis pub/sub code | Dapr Pub/Sub API — pluggable message broker |
| **Service invocation** | Direct HTTP/gRPC calls with service discovery | Dapr Service Invocation — built-in mTLS, retries, load balancing |
| **Secrets access** | Provider-specific SDK (AWS/Azure/Vault) | Dapr Secrets API — unified access across providers |
| **Event triggers** | Custom webhook/polling code | Dapr Input Bindings — standardized event ingestion |
| **Distributed locking** | Redis/Zookeeper client code | Dapr Distributed Lock API |

### Dapr's Position in the Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                              │
│                                                                     │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  │
│  │   LangGraph Executor Pod    │  │   LangGraph Worker Pod      │  │
│  │  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │  │
│  │  │  LangGraph App        │  │  │  │  LangGraph App        │  │  │
│  │  │  (graph executor)     │  │  │  │  (background worker)  │  │  │
│  │  └──────────┬────────────┘  │  │  └──────────┬────────────┘  │  │
│  │             │ localhost      │  │             │ localhost      │  │
│  │  ┌──────────▼────────────┐  │  │  ┌──────────▼────────────┐  │  │
│  │  │  Dapr Sidecar         │  │  │  │  Dapr Sidecar         │  │  │
│  │  │  ┌─────┐ ┌──────┐    │  │  │  │  ┌─────┐ ┌──────┐    │  │  │
│  │  │  │State│ │Pub/  │    │  │  │  │  │State│ │Pub/  │    │  │  │
│  │  │  │ API │ │Sub   │    │  │  │  │  │ API │ │Sub   │    │  │  │
│  │  │  └──┬──┘ └──┬───┘    │  │  │  │  └──┬──┘ └──┬───┘    │  │  │
│  │  │  ┌──┴──┐ ┌──┴───┐   │  │  │  │  ┌──┴──┐ ┌──┴───┐   │  │  │
│  │  │  │Secr.│ │Serv.  │   │  │  │  │  │Secr.│ │Serv.  │   │  │  │
│  │  │  │ API │ │Invoc. │   │  │  │  │  │ API │ │Invoc. │   │  │  │
│  │  │  └─────┘ └───────┘   │  │  │  │  └─────┘ └───────┘   │  │  │
│  │  └───────────────────────┘  │  │  └───────────────────────┘  │  │
│  └─────────────────────────────┘  └─────────────────────────────┘  │
│                    │                             │                  │
│                    ▼                             ▼                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │PostgreSQL│  │ Redis    │  │ Kafka    │  │ Vault / K8s      │   │
│  │(state)   │  │(pub/sub) │  │(events)  │  │ Secrets          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Dapr Control Plane (Operator, Sentry, Placement, Injector) │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

Dapr sits **as a sidecar inside each pod**, intercepting all distributed communication. The LangGraph application talks to `localhost` Dapr APIs instead of directly connecting to PostgreSQL, Redis, Kafka, or secret stores. Dapr's control plane handles mTLS, service discovery, and component configuration.

### Dapr Configuration for LangGraph

#### State Store Component (Checkpoint Persistence)

```yaml
# Dapr state store component backed by PostgreSQL
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: langgraph-checkpoints
spec:
  type: state.postgresql
  version: v1
  metadata:
    - name: connectionString
      secretKeyRef:
        name: langgraph-secrets
        key: checkpoint-db-url
    - name: actorStateStore
      value: "true"
  scopes:
    - langgraph-executor    # Only these apps can access this state store
    - langgraph-worker
```

**Using Dapr State API in LangGraph:**
```python
import httpx

DAPR_HTTP_PORT = 3500
STATE_STORE_NAME = "langgraph-checkpoints"

async def save_checkpoint(thread_id: str, state: dict):
    """Save LangGraph checkpoint via Dapr State API."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{STATE_STORE_NAME}",
            json=[{
                "key": f"checkpoint:{thread_id}",
                "value": state,
                "options": {
                    "consistency": "strong",
                    "concurrency": "first-write",
                },
            }],
        )

async def load_checkpoint(thread_id: str) -> dict:
    """Load LangGraph checkpoint via Dapr State API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{STATE_STORE_NAME}/checkpoint:{thread_id}",
        )
        return resp.json() if resp.status_code == 200 else {}
```

#### Pub/Sub Component (Inter-Agent Communication)

```yaml
# Dapr pub/sub component backed by Redis
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: agent-events
spec:
  type: pubsub.redis
  version: v1
  metadata:
    - name: redisHost
      value: redis.default.svc.cluster.local:6379
    - name: redisPassword
      secretKeyRef:
        name: redis-secrets
        key: password
```

**Publishing agent events:**
```python
async def publish_agent_event(topic: str, event: dict):
    """Publish an agent event via Dapr Pub/Sub."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish/agent-events/{topic}",
            json=event,
        )

# Example: Publish when a graph run completes
await publish_agent_event("graph.completed", {
    "thread_id": thread_id,
    "graph_name": "analyst",
    "status": "success",
    "duration_ms": elapsed_ms,
})
```

#### Secrets Component

```yaml
# Dapr secrets component — Kubernetes secrets backend
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: k8s-secrets
spec:
  type: secretstores.kubernetes
  version: v1
```

**Accessing secrets from LangGraph:**
```python
async def get_secret(store: str, key: str) -> str:
    """Retrieve secret via Dapr Secrets API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{DAPR_HTTP_PORT}/v1.0/secrets/{store}/{key}",
        )
        return resp.json()[key]

# Usage — no cloud-specific SDK needed
llm_api_key = await get_secret("k8s-secrets", "openai-api-key")
```

#### Service Invocation (Agent-to-Agent)

```python
async def invoke_specialist_agent(agent_name: str, payload: dict) -> dict:
    """Invoke another LangGraph agent via Dapr Service Invocation (with mTLS)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{DAPR_HTTP_PORT}/v1.0/invoke/{agent_name}/method/run",
            json=payload,
        )
        return resp.json()

# Example: Supervisor agent delegates to specialist
research_result = await invoke_specialist_agent("research-agent", {
    "task": "Find latest revenue data for Q4",
    "thread_id": thread_id,
})
```

---

## 3. Combined Architecture: LangGraph + KEDA + Dapr on Kubernetes

When KEDA and Dapr are combined, they provide a complete **production runtime** for LangGraph on Kubernetes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                                   │
│                                                                             │
│  ┌─────────────────────┐     ┌──────────────────────────────────────────┐   │
│  │   KEDA Operator      │     │   Dapr Control Plane                    │   │
│  │                      │     │   (Sentry · Operator · Placement)       │   │
│  │  • ScaledObject      │     │   • mTLS cert management                │   │
│  │    controller         │     │   • Sidecar injection                   │   │
│  │  • Metrics adapter   │     │   • Component resolution                │   │
│  └──────────┬───────────┘     └──────────────────────────────────────────┘   │
│             │ scales                                                        │
│             ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    LangGraph Executor Pods                           │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐             │   │
│  │  │ Pod 1                  │  │ Pod N                  │             │   │
│  │  │ ┌────────────────────┐ │  │ ┌────────────────────┐ │   ...       │   │
│  │  │ │  LangGraph App     │ │  │ │  LangGraph App     │ │             │   │
│  │  │ │  • Graph executor  │ │  │ │  • Graph executor  │ │             │   │
│  │  │ │  • FastAPI server  │ │  │ │  • FastAPI server  │ │             │   │
│  │  │ └────────┬───────────┘ │  │ └────────┬───────────┘ │             │   │
│  │  │ ┌────────▼───────────┐ │  │ ┌────────▼───────────┐ │             │   │
│  │  │ │  Dapr Sidecar      │ │  │ │  Dapr Sidecar      │ │             │   │
│  │  │ │  (state/pub/secret)│ │  │ │  (state/pub/secret)│ │             │   │
│  │  │ └────────────────────┘ │  │ └────────────────────┘ │             │   │
│  │  └────────────────────────┘  └────────────────────────┘             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│             │                              │                                │
│    ┌────────▼─────────────────────────────▼────────────────────┐            │
│    │              Shared Infrastructure                         │            │
│    │  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │            │
│    │  │ PostgreSQL │  │  Redis   │  │  Kafka   │  │ Vault  │  │            │
│    │  │ (state)    │  │ (queue + │  │ (events) │  │(secrets)│  │            │
│    │  │            │  │  pub/sub)│  │          │  │        │  │            │
│    │  └────────────┘  └──────────┘  └──────────┘  └────────┘  │            │
│    └───────────────────────────────────────────────────────────┘            │
│                                                                             │
│    ┌────────────────────────────────────────────────────────────┐           │
│    │         Observability Stack                                │           │
│    │  ┌─────────────┐  ┌───────────┐  ┌──────────┐  ┌───────┐ │           │
│    │  │ OTel        │  │Prometheus │  │ Loki     │  │Grafana│ │           │
│    │  │ Collector   │  │           │  │          │  │       │ │           │
│    │  └─────────────┘  └───────────┘  └──────────┘  └───────┘ │           │
│    └────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How KEDA and Dapr Complement Each Other

| Responsibility | KEDA | Dapr |
|---|---|---|
| **When to scale** | ✅ Event-driven scaling decisions | — |
| **How many replicas** | ✅ Adjusts replica count | — |
| **Scale to zero** | ✅ Native support | — |
| **State management** | — | ✅ Pluggable state stores |
| **Inter-service communication** | — | ✅ Service invocation + mTLS |
| **Pub/Sub messaging** | — | ✅ Pluggable message brokers |
| **Secrets management** | — | ✅ Unified secrets API |
| **Distributed locking** | — | ✅ Lock API |
| **mTLS between pods** | — | ✅ Automatic via Sentry |

KEDA decides **when and how much** to scale; Dapr provides the **runtime capabilities** each scaled instance needs. Together, they eliminate custom infrastructure code from LangGraph applications.

### End-to-End Request Flow

```
User Request
    │
    ▼
┌───────────────┐
│ Load Balancer │
└───────┬───────┘
        │
        ▼
┌───────────────────────────────┐
│ LangGraph Executor Pod        │
│ ┌───────────────────────────┐ │
│ │ FastAPI receives request  │ │
│ │ → Dapr Secrets API (key)  │─┼─→ Vault: fetch LLM API key
│ │ → Dapr State API (load)   │─┼─→ PostgreSQL: load checkpoint
│ │ → Execute graph nodes     │ │
│ │ → LLM API call            │─┼─→ OpenAI / Azure / local model
│ │ → Dapr State API (save)   │─┼─→ PostgreSQL: save checkpoint
│ │ → Dapr Pub/Sub (event)    │─┼─→ Redis: publish "graph.completed"
│ │ → Return response         │ │
│ └───────────────────────────┘ │
│ ┌───────────────────────────┐ │
│ │ Dapr Sidecar (mTLS,      │ │
│ │ retries, observability)   │ │
│ └───────────────────────────┘ │
└───────────────────────────────┘
        │
        │  Meanwhile, KEDA monitors:
        │  • Redis queue depth → scales executor replicas
        │  • Prometheus active_runs → adjusts capacity
        │  • Cron schedule → pre-warms for business hours
```

---

## 4. Monitoring Dimension 1: Agent-Level Logging & Tracing

Agent-level observability captures what each **agent/graph node is doing** — every decision, LLM call, tool invocation, and state transition.

### What Specific Data to Capture

| Data Point | Description | Format | Example |
|---|---|---|---|
| **Graph run ID** | Unique identifier for each graph execution | `UUID` | `run-a1b2c3d4` |
| **Thread ID** | Conversation/session thread | `string` | `thread-xyz-789` |
| **Node name** | Which graph node is executing | `string` | `researcher`, `analyst` |
| **Node entry/exit timestamps** | When a node started and finished | `ISO 8601` | `2025-01-15T10:30:00.123Z` |
| **Node duration** | Time spent in the node (ms) | `float` | `2450.5` |
| **LLM model used** | Which model was invoked | `string` | `gpt-4o`, `claude-3.5-sonnet` |
| **LLM prompt tokens** | Input tokens sent to LLM | `int` | `1250` |
| **LLM completion tokens** | Output tokens received | `int` | `340` |
| **LLM latency** | Time for LLM response | `float (ms)` | `1800.2` |
| **Tool name** | Which tool was invoked | `string` | `web_search`, `db_query` |
| **Tool input** | Parameters passed to tool (sanitized) | `JSON` | `{"query": "Q4 revenue"}` |
| **Tool output summary** | Truncated tool response | `string` | `"Found 15 results..."` |
| **Tool success/failure** | Whether the tool call succeeded | `bool` | `true` |
| **Tool latency** | Tool execution time | `float (ms)` | `350.0` |
| **State transitions** | Edge traversed in graph | `string` | `researcher → analyst` |
| **Conditional routing decisions** | Why a specific edge was chosen | `string` | `"needs_more_data → researcher"` |
| **Recursion depth** | Current superstep count | `int` | `3 of 25` |
| **Error type & message** | Exception details on failure | `string` | `TimeoutError: LLM call exceeded 30s` |
| **Checkpoint saved** | Whether state was persisted | `bool` | `true` |

### Implementation: OpenTelemetry Instrumented Nodes

```python
from opentelemetry import trace, metrics
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer("langgraph.agents")
meter = metrics.get_meter("langgraph.agents")

# Metrics instruments
node_duration = meter.create_histogram("agent.node.duration_ms", unit="ms")
llm_tokens = meter.create_counter("agent.llm.tokens")
tool_calls = meter.create_counter("agent.tool.calls")

def instrument_node(node_name: str, node_fn):
    """Wrap a LangGraph node with full agent-level telemetry."""
    async def wrapper(state: dict, config: dict) -> dict:
        thread_id = config.get("configurable", {}).get("thread_id", "")
        run_id = config.get("configurable", {}).get("run_id", "")

        with tracer.start_as_current_span(
            f"agent.node.{node_name}",
            attributes={
                "agent.node.name": node_name,
                "agent.thread_id": thread_id,
                "agent.run_id": run_id,
                "agent.graph_name": config.get("configurable", {}).get("graph_name", ""),
            },
        ) as span:
            start = time.monotonic()
            try:
                result = await node_fn(state, config)
                duration = (time.monotonic() - start) * 1000

                span.set_status(StatusCode.OK)
                span.set_attribute("agent.node.duration_ms", duration)
                span.set_attribute("agent.node.success", True)
                node_duration.record(duration, {"node": node_name})

                return result
            except Exception as e:
                duration = (time.monotonic() - start) * 1000
                span.set_status(StatusCode.ERROR, str(e))
                span.set_attribute("agent.node.success", False)
                span.set_attribute("agent.error.type", type(e).__name__)
                span.set_attribute("agent.error.message", str(e))
                span.record_exception(e)
                node_duration.record(duration, {"node": node_name, "error": "true"})
                raise

    return wrapper
```

### Implementation: LLM Call Tracing

```python
from langchain_core.callbacks import BaseCallbackHandler

class OTelLLMTracer(BaseCallbackHandler):
    """Trace every LLM call with OpenTelemetry spans."""

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._span = tracer.start_span(
            "agent.llm.call",
            attributes={
                "agent.llm.model": serialized.get("kwargs", {}).get("model", "unknown"),
                "agent.llm.prompt_length": sum(len(p) for p in prompts),
            },
        )

    def on_llm_end(self, response, **kwargs):
        usage = response.llm_output.get("token_usage", {})
        self._span.set_attribute("agent.llm.prompt_tokens", usage.get("prompt_tokens", 0))
        self._span.set_attribute("agent.llm.completion_tokens", usage.get("completion_tokens", 0))
        self._span.set_attribute("agent.llm.total_tokens", usage.get("total_tokens", 0))
        self._span.set_status(StatusCode.OK)
        self._span.end()

        llm_tokens.add(usage.get("prompt_tokens", 0), {"direction": "input"})
        llm_tokens.add(usage.get("completion_tokens", 0), {"direction": "output"})

    def on_llm_error(self, error, **kwargs):
        self._span.set_status(StatusCode.ERROR, str(error))
        self._span.record_exception(error)
        self._span.end()
```

---

## 5. Monitoring Dimension 2: User-Level Tracking

User-level tracking captures **who** is using the system, their interaction patterns, satisfaction, and session behavior.

### What Specific Data to Capture

| Data Point | Description | Format | Example |
|---|---|---|---|
| **User ID** | Authenticated user identifier | `string` | `user-john-doe-001` |
| **Session ID** | User session identifier | `UUID` | `sess-e5f6a7b8` |
| **Thread ID** | Conversation thread | `string` | `thread-xyz-789` |
| **Request timestamp** | When the user sent a request | `ISO 8601` | `2025-01-15T10:30:00Z` |
| **Response timestamp** | When the response was delivered | `ISO 8601` | `2025-01-15T10:30:05Z` |
| **End-to-end latency** | Total time from request to response | `float (ms)` | `5200.0` |
| **User query** | The input message (sanitized for PII) | `string` | `"Summarize Q4 revenue trends"` |
| **Response quality signal** | Thumbs up/down, rating | `enum` | `positive`, `negative`, `neutral` |
| **Conversation turn count** | Number of turns in session | `int` | `7` |
| **Token usage per user** | Cumulative tokens consumed | `int` | `12500` |
| **Cost per user** | Estimated cost attributed to user | `float` | `$0.42` |
| **Tools used** | Which tools the user's request triggered | `list[str]` | `["db_query", "chart_gen"]` |
| **Error experienced** | Whether the user saw an error | `bool` | `false` |
| **User department / team** | Organizational unit (from IAM) | `string` | `Finance` |
| **Graph name** | Which agent workflow was invoked | `string` | `financial-analyst` |
| **Feedback text** | Free-form user feedback | `string` | `"The chart was helpful"` |
| **Escalation to human** | Whether HITL was triggered | `bool` | `false` |

### Implementation: User Tracking Middleware

```python
import time
import uuid
from fastapi import Request

@api.middleware("http")
async def user_tracking_middleware(request: Request, call_next):
    """Track user-level metrics for every request."""
    start = time.monotonic()
    request_id = str(uuid.uuid4())
    user = getattr(request.state, "user", {})
    user_id = user.get("sub", "anonymous")

    with tracer.start_as_current_span(
        "user.request",
        attributes={
            "user.id": user_id,
            "user.department": user.get("department", "unknown"),
            "user.session_id": request.headers.get("X-Session-ID", ""),
            "user.request_id": request_id,
            "http.method": request.method,
            "http.url": str(request.url),
        },
    ) as span:
        response = await call_next(request)
        duration = (time.monotonic() - start) * 1000

        span.set_attribute("user.response_time_ms", duration)
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("user.error", response.status_code >= 400)

        # Record user-level metrics
        user_requests.labels(user_id=user_id, status=str(response.status_code)).inc()
        user_latency.labels(user_id=user_id).observe(duration / 1000)

        return response
```

### Implementation: User Feedback Capture

```python
from pydantic import BaseModel
from enum import Enum

class FeedbackRating(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class UserFeedback(BaseModel):
    thread_id: str
    run_id: str
    rating: FeedbackRating
    comment: str = ""

@api.post("/feedback")
async def submit_feedback(feedback: UserFeedback, user=Depends(verify_token)):
    """Capture user feedback and correlate with agent traces."""
    with tracer.start_as_current_span(
        "user.feedback",
        attributes={
            "user.id": user["sub"],
            "user.feedback.thread_id": feedback.thread_id,
            "user.feedback.run_id": feedback.run_id,
            "user.feedback.rating": feedback.rating.value,
        },
    ):
        await store_feedback(
            user_id=user["sub"],
            thread_id=feedback.thread_id,
            run_id=feedback.run_id,
            rating=feedback.rating,
            comment=feedback.comment,
        )

        feedback_counter.labels(rating=feedback.rating.value).inc()

    return {"status": "recorded"}
```

---

## 6. Monitoring Dimension 3: Hardware & Infrastructure Metrics

Infrastructure metrics capture the health and resource utilization of the **underlying compute, storage, and network**.

### What Specific Data to Capture

| Data Point | Source | Metric Name | Description |
|---|---|---|---|
| **CPU utilization** | kubelet / cAdvisor | `container_cpu_usage_seconds_total` | CPU seconds consumed per pod |
| **Memory utilization** | kubelet / cAdvisor | `container_memory_working_set_bytes` | Active memory per pod |
| **Memory OOM events** | kubelet | `kube_pod_container_status_last_terminated_reason` | OOM kill count |
| **Pod restart count** | kube-state-metrics | `kube_pod_container_status_restarts_total` | Crash/restart frequency |
| **Pod ready status** | kube-state-metrics | `kube_pod_status_ready` | Is the pod serving traffic |
| **Node CPU** | node-exporter | `node_cpu_seconds_total` | Host-level CPU usage |
| **Node memory** | node-exporter | `node_memory_MemAvailable_bytes` | Available host memory |
| **Disk I/O** | node-exporter | `node_disk_io_time_seconds_total` | Disk busy time |
| **Disk space** | node-exporter | `node_filesystem_avail_bytes` | Available disk space |
| **Network I/O** | node-exporter | `node_network_transmit_bytes_total` | Network traffic out |
| **GPU utilization** | DCGM exporter | `DCGM_FI_DEV_GPU_UTIL` | GPU usage % (if local LLM) |
| **GPU memory** | DCGM exporter | `DCGM_FI_DEV_FB_USED` | GPU memory used (if local LLM) |
| **HPA replica count** | kube-state-metrics | `kube_horizontalpodautoscaler_status_current_replicas` | Current/desired replicas |
| **KEDA scaled replicas** | KEDA metrics | `keda_scaler_metrics_value` | KEDA scaler metric value |
| **KEDA scaling activity** | KEDA metrics | `keda_scaled_object_errors` | KEDA scaling errors |
| **PostgreSQL connections** | pg_exporter | `pg_stat_activity_count` | Active DB connections |
| **PostgreSQL query latency** | pg_exporter | `pg_stat_statements_mean_time_seconds` | Avg query time |
| **PostgreSQL table size** | pg_exporter | `pg_total_relation_size_bytes` | Checkpoints table size |
| **Redis memory** | redis-exporter | `redis_memory_used_bytes` | Redis memory consumption |
| **Redis queue length** | redis-exporter | `redis_list_length` | Pending task queue depth |

### Implementation: Prometheus Monitoring Stack

```yaml
# Install kube-prometheus-stack via Helm
# Includes: Prometheus, Grafana, node-exporter, kube-state-metrics, alertmanager
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword=your-secure-password

# Additional exporters for LangGraph infrastructure
# PostgreSQL exporter
helm install pg-exporter prometheus-community/prometheus-postgres-exporter \
  --namespace monitoring \
  --set config.datasource.host=checkpoint-db.default.svc.cluster.local

# Redis exporter
helm install redis-exporter prometheus-community/prometheus-redis-exporter \
  --namespace monitoring \
  --set redisAddress=redis://redis.default.svc.cluster.local:6379
```

### KEDA-Specific Metrics

```yaml
# ServiceMonitor to scrape KEDA metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: keda-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: keda-operator
  endpoints:
    - port: metrics
      interval: 15s
```

### Key Infrastructure Alerts

```yaml
# PrometheusRule for LangGraph infrastructure alerts
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: langgraph-infra-alerts
  namespace: monitoring
spec:
  groups:
    - name: langgraph.infrastructure
      rules:
        - alert: ExecutorHighCPU
          expr: |
            rate(container_cpu_usage_seconds_total{
              pod=~"langgraph-executor.*"
            }[5m]) > 0.9
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "LangGraph executor CPU > 90%"

        - alert: CheckpointDBHighConnections
          expr: pg_stat_activity_count > 80
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "Checkpoint DB connection count > 80"

        - alert: RedisQueueBacklog
          expr: redis_list_length{list="langgraph:task_queue"} > 100
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Task queue backlog > 100 items"

        - alert: KEDAScalingErrors
          expr: rate(keda_scaled_object_errors[5m]) > 0
          for: 3m
          labels:
            severity: critical
          annotations:
            summary: "KEDA is failing to scale LangGraph workloads"

        - alert: PodOOMKilled
          expr: |
            kube_pod_container_status_last_terminated_reason{
              reason="OOMKilled", pod=~"langgraph.*"
            } > 0
          labels:
            severity: critical
          annotations:
            summary: "LangGraph pod OOM killed"
```

---

## 7. Monitoring Dimension 4: Application Logs

Application logs capture the structured output from the **LangGraph application code**, Dapr sidecars, and supporting services.

### What Specific Data to Capture

| Data Point | Description | Log Field | Example |
|---|---|---|---|
| **Timestamp** | When the event occurred | `timestamp` | `2025-01-15T10:30:00.123Z` |
| **Log level** | Severity | `level` | `INFO`, `WARN`, `ERROR` |
| **Service name** | Which microservice emitted the log | `service` | `langgraph-executor` |
| **Pod name** | Kubernetes pod | `pod` | `langgraph-executor-7d8f9-abc12` |
| **Trace ID** | OpenTelemetry trace correlation | `trace_id` | `4bf92f3577b34da6a3ce929d0e0e4736` |
| **Span ID** | Specific span within trace | `span_id` | `00f067aa0ba902b7` |
| **Thread ID** | LangGraph conversation thread | `thread_id` | `thread-xyz-789` |
| **Run ID** | Graph execution run identifier | `run_id` | `run-a1b2c3d4` |
| **User ID** | Authenticated user | `user_id` | `user-john-doe-001` |
| **Event type** | Categorized event | `event` | `graph_started`, `node_completed`, `llm_call`, `tool_error` |
| **Graph name** | Which graph is executing | `graph_name` | `financial-analyst` |
| **Node name** | Active node | `node_name` | `researcher` |
| **Message** | Human-readable log message | `message` | `"Node 'researcher' completed in 2.4s"` |
| **Error stack trace** | Full exception trace on errors | `stack_trace` | Python traceback |
| **HTTP status code** | API response code | `http_status` | `200`, `500` |
| **Request path** | API endpoint | `http_path` | `/run` |
| **Dapr component** | Dapr building block used | `dapr_component` | `state.postgresql`, `pubsub.redis` |
| **Dapr operation** | Dapr API operation | `dapr_operation` | `state.save`, `publish` |

### Implementation: Structured Logging with Trace Correlation

```python
import structlog
from opentelemetry import trace

def add_trace_context(logger, method_name, event_dict):
    """Inject OpenTelemetry trace context into every log entry."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_trace_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

# Usage in LangGraph node
async def researcher_node(state: dict, config: dict) -> dict:
    thread_id = config["configurable"]["thread_id"]
    structlog.contextvars.bind_contextvars(
        thread_id=thread_id,
        run_id=config["configurable"].get("run_id", ""),
        user_id=config["configurable"].get("user_id", ""),
        graph_name="financial-analyst",
        node_name="researcher",
    )

    logger.info("node_started", event="node_started")

    try:
        result = await do_research(state)
        logger.info(
            "node_completed",
            event="node_completed",
            duration_ms=result.get("duration_ms"),
            tools_used=result.get("tools_used", []),
        )
        return result
    except Exception as e:
        logger.error(
            "node_failed",
            event="node_failed",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise
```

### Log Output Example (JSON)

```json
{
  "timestamp": "2025-01-15T10:30:02.456Z",
  "level": "info",
  "event": "node_completed",
  "message": "node_completed",
  "service": "langgraph-executor",
  "pod": "langgraph-executor-7d8f9-abc12",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "thread_id": "thread-xyz-789",
  "run_id": "run-a1b2c3d4",
  "user_id": "user-john-doe-001",
  "graph_name": "financial-analyst",
  "node_name": "researcher",
  "duration_ms": 2450.5,
  "tools_used": ["web_search", "db_query"]
}
```

---

## 8. Centralized Observability: Aggregation, Correlation & Dashboarding

### The Aggregation Challenge

In a LangGraph + KEDA + Dapr deployment, observability data flows from **multiple sources in different formats**:

| Data Stream | Source | Format | Volume |
|---|---|---|---|
| Agent traces | LangGraph nodes, LLM calls, tool calls | OpenTelemetry spans | Medium |
| User tracking | FastAPI middleware, feedback API | OTel spans + metrics | Low–Medium |
| Infrastructure metrics | kubelet, node-exporter, kube-state-metrics, KEDA, pg-exporter | Prometheus metrics | High |
| Application logs | LangGraph app, Dapr sidecars, K8s events | Structured JSON logs | High |

The goal is to **funnel all four streams into a single observability platform** where they can be correlated, queried, dashboarded, and alerted on.

### Architecture: OpenTelemetry Collector as the Unified Pipeline

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                       │
│                                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Agent Traces  │  │ User Spans   │  │ Infra Metrics│  │ App Logs     │  │
│  │ (OTel SDK)    │  │ (OTel SDK)   │  │ (Prometheus) │  │ (structlog)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │                 │           │
│         ▼                 ▼                 ▼                 ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                  OpenTelemetry Collector                            │  │
│  │                                                                     │  │
│  │  Receivers:                                                         │  │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────────┐ ┌────────────┐  │  │
│  │  │ OTLP     │ │ Prometheus   │ │ Filelog        │ │ K8s Events │  │  │
│  │  │ (traces, │ │ Receiver     │ │ Receiver       │ │ Receiver   │  │  │
│  │  │ metrics) │ │ (scrape)     │ │ (container     │ │            │  │  │
│  │  │          │ │              │ │  logs)         │ │            │  │  │
│  │  └──────────┘ └──────────────┘ └────────────────┘ └────────────┘  │  │
│  │                                                                     │  │
│  │  Processors:                                                        │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │  │
│  │  │ k8sattributes│ │ Resource     │ │ Batch        │               │  │
│  │  │ (enrich with │ │ Detection    │ │ Processor    │               │  │
│  │  │  pod, node)  │ │ (service     │ │ (buffering)  │               │  │
│  │  │              │ │  metadata)   │ │              │               │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘               │  │
│  │                                                                     │  │
│  │  Exporters:                                                         │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │  │
│  │  │ Tempo        │ │ Prometheus   │ │ Loki         │               │  │
│  │  │ (traces)     │ │ Remote Write │ │ (logs)       │               │  │
│  │  │              │ │ (metrics)    │ │              │               │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│         │                 │                 │                              │
│         ▼                 ▼                 ▼                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │ Tempo        │  │ Prometheus   │  │ Loki         │                    │
│  │ (trace store)│  │ (metrics     │  │ (log store)  │                    │
│  │              │  │  store)      │  │              │                    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                    │
│         │                 │                 │                              │
│         └─────────────────┼─────────────────┘                              │
│                           ▼                                                │
│                  ┌─────────────────┐                                       │
│                  │    Grafana       │                                       │
│                  │  (unified UI)   │                                       │
│                  │                 │                                       │
│                  │  • Dashboards   │                                       │
│                  │  • Correlation  │                                       │
│                  │  • Alerting     │                                       │
│                  │  • Explore      │                                       │
│                  └─────────────────┘                                       │
└────────────────────────────────────────────────────────────────────────────┘
```

### OpenTelemetry Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  # Receive traces and metrics from LangGraph app (OTel SDK)
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Scrape Prometheus metrics from infrastructure
  prometheus:
    config:
      scrape_configs:
        - job_name: langgraph-executors
          kubernetes_sd_configs:
            - role: pod
          relabel_configs:
            - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
              action: keep
              regex: "true"
        - job_name: keda-metrics
          static_configs:
            - targets: ["keda-operator.keda:8080"]
        - job_name: dapr-metrics
          kubernetes_sd_configs:
            - role: pod
          relabel_configs:
            - source_labels: [__meta_kubernetes_pod_container_name]
              action: keep
              regex: daprd

  # Collect container logs from Kubernetes
  filelog:
    include: [/var/log/pods/default_langgraph-*/*/*.log]
    operators:
      - type: json_parser
        timestamp:
          parse_from: attributes.timestamp
          layout: "%Y-%m-%dT%H:%M:%S.%LZ"
      # Extract trace_id from structured logs for correlation
      - type: move
        from: attributes.trace_id
        to: resource["trace_id"]
      - type: move
        from: attributes.thread_id
        to: resource["langgraph.thread_id"]

  # Kubernetes events (scaling events, pod lifecycle)
  k8s_events:
    namespaces: [default, keda]

processors:
  # Enrich all telemetry with Kubernetes metadata
  k8sattributes:
    extract:
      metadata:
        - k8s.pod.name
        - k8s.namespace.name
        - k8s.node.name
        - k8s.deployment.name
    pod_association:
      - sources:
          - from: resource_attribute
            name: k8s.pod.ip

  # Add service-level resource attributes
  resource:
    attributes:
      - key: environment
        value: production
        action: upsert
      - key: team
        value: ai-platform
        action: upsert

  # Batch for performance
  batch:
    timeout: 5s
    send_batch_size: 1024

exporters:
  # Traces → Tempo
  otlp/tempo:
    endpoint: tempo.monitoring:4317
    tls:
      insecure: true

  # Metrics → Prometheus
  prometheusremotewrite:
    endpoint: http://prometheus.monitoring:9090/api/v1/write

  # Logs → Loki
  loki:
    endpoint: http://loki.monitoring:3100/loki/api/v1/push
    labels:
      resource:
        service.name: "service"
        k8s.pod.name: "pod"
        k8s.namespace.name: "namespace"
      attributes:
        level: ""
        event: ""
        thread_id: ""

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [k8sattributes, resource, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp, prometheus]
      processors: [k8sattributes, resource, batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [filelog, k8s_events]
      processors: [k8sattributes, resource, batch]
      exporters: [loki]
```

### Correlation: Connecting All Four Dimensions

The **key to unified observability** is a shared set of correlation identifiers that link data across all four streams:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Correlation Keys                              │
│                                                                 │
│  trace_id ─────── Links traces ↔ logs ↔ user spans             │
│  thread_id ────── Links all data for a conversation             │
│  run_id ────────── Links all data for a single graph execution   │
│  user_id ──────── Links all data for a specific user            │
│  pod_name ──────── Links app data to infrastructure metrics      │
│  service_name ──── Links all data from the same service          │
└─────────────────────────────────────────────────────────────────┘
```

| Correlation Scenario | Primary Key | How It Works |
|---|---|---|
| **Trace → Logs** | `trace_id` | Structured logs include the OTel `trace_id`; Grafana Tempo → Loki link |
| **Trace → Metrics** | `service_name`, `pod_name` | OTel resource attributes match Prometheus labels |
| **User → Agent traces** | `thread_id`, `run_id` | User request span and agent node spans share `thread_id` |
| **User → Cost** | `user_id` | Token usage metrics tagged with `user_id` |
| **Agent → Infrastructure** | `pod_name` | Agent spans tagged with `k8s.pod.name` match cAdvisor metrics |
| **KEDA scaling → Queue depth** | `keda_scaler_metrics_value` + `redis_list_length` | Both scraped by Prometheus |
| **Dapr calls → Agent traces** | `trace_id` (propagated by Dapr) | Dapr propagates W3C trace context through sidecar |

**How Dapr Enables Correlation:**

Dapr automatically propagates W3C Trace Context headers (`traceparent`, `tracestate`) through its sidecar for service invocation and pub/sub. This means when a LangGraph executor calls another service via Dapr, the **same trace_id flows through both sides** — enabling end-to-end trace correlation without manual header propagation.

### Grafana Dashboards

#### Dashboard 1: Agent Operations Overview

```
┌────────────────────────────────────────────────────────────────┐
│  AGENT OPERATIONS OVERVIEW                      [Last 6 hours] │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Total    │  │ Success  │  │ Avg      │  │ Active   │       │
│  │ Runs     │  │ Rate     │  │ Latency  │  │ Runs     │       │
│  │  1,247   │  │  97.2%   │  │  4.2s    │  │   12     │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  Graph Runs Over Time          │  Error Rate by Node            │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ ▄▄▆█▇▆▄▃▃▄▅▆▇█▇▅▃▂  │     │  │ researcher: 1.2%     │    │
│  │                       │     │  │ analyst:     0.8%     │    │
│  │                       │     │  │ writer:      3.1%     │    │
│  └───────────────────────┘     │  └───────────────────────┘    │
│                                                                 │
│  Node Latency (p50 / p95 / p99)│  Token Usage by Model         │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ researcher: 2.1/4.5/8s│     │  │ gpt-4o:    45,200     │    │
│  │ analyst:    1.5/3.2/5s│     │  │ gpt-4o-mini: 23,100   │    │
│  │ writer:     3.2/6.1/9s│     │  │ o3-mini:    8,400     │    │
│  └───────────────────────┘     │  └───────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

**Grafana Query Examples:**

```promql
# Total graph runs (success vs. failure)
sum(rate(langgraph_graph_runs_total[5m])) by (status)

# p95 node latency
histogram_quantile(0.95, rate(langgraph_node_duration_seconds_bucket[5m]))

# Active runs
langgraph_active_runs

# Token consumption rate
sum(rate(langgraph_llm_tokens_total[1h])) by (model, direction)
```

#### Dashboard 2: User Experience

```
┌────────────────────────────────────────────────────────────────┐
│  USER EXPERIENCE                                [Last 24 hours]│
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Active   │  │ Avg      │  │ Positive │  │ Errors   │       │
│  │ Users    │  │ Response │  │ Feedback │  │ Rate     │       │
│  │   83     │  │  4.2s    │  │  89%     │  │  2.1%    │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  User Latency (p50/p95)        │  Top Users by Token Usage     │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ p50: ██████ 3.1s      │     │  │ user-042: 45,200 tkns│    │
│  │ p95: █████████ 8.2s   │     │  │ user-017: 32,100 tkns│    │
│  └───────────────────────┘     │  └───────────────────────┘    │
│                                                                 │
│  Feedback Distribution         │  Usage by Department           │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ 👍 89%  👎 7%  — 4%   │     │  │ Finance:    42%       │    │
│  └───────────────────────┘     │  │ Marketing:  28%       │    │
│                                 │  │ Engineering:18%       │    │
│                                 │  │ HR:         12%       │    │
│                                 │  └───────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

#### Dashboard 3: Infrastructure & Scaling

```
┌────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE & SCALING                       [Last 1 hour]  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Executor │  │ Avg CPU  │  │ Avg Mem  │  │ Queue    │       │
│  │ Replicas │  │          │  │          │  │ Depth    │       │
│  │    8     │  │  62%     │  │  1.8 Gi  │  │    3     │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  KEDA Scaling Activity         │  CPU / Memory per Pod          │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ Replicas: ▂▃▅▇█▇▅▃▂  │     │  │ Pod 1: CPU 65% M 1.2G│    │
│  │ Desired:  ▂▃▅▇█▇▅▃▂  │     │  │ Pod 2: CPU 71% M 1.5G│    │
│  └───────────────────────┘     │  │ Pod 3: CPU 58% M 1.1G│    │
│                                 │  └───────────────────────┘    │
│  PostgreSQL Health             │  Redis Health                  │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ Connections: 24/100   │     │  │ Memory: 256MB/1GB     │    │
│  │ Avg Query: 3.2ms      │     │  │ Queue Length: 3       │    │
│  │ Table Size: 2.1 GB    │     │  │ Ops/sec: 1,250        │    │
│  └───────────────────────┘     │  └───────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

#### Dashboard 4: Cost & Budget

```
┌────────────────────────────────────────────────────────────────┐
│  COST & BUDGET                                  [Last 30 days] │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Total    │  │ LLM Cost │  │ Infra    │  │ Budget   │       │
│  │ Cost     │  │          │  │ Cost     │  │ Used     │       │
│  │  $4,230  │  │  $3,150  │  │  $1,080  │  │  72%     │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
│  Cost Trend (daily)            │  Cost by Team                  │
│  ┌───────────────────────┐     │  ┌───────────────────────┐    │
│  │ █▇▆▇█▇▆▅▆▇█▆▅▆▇█▇▆  │     │  │ Finance:    $1,890    │    │
│  │                       │     │  │ Marketing:  $1,230    │    │
│  │ — Budget line ———— —  │     │  │ Engineering:  $750    │    │
│  └───────────────────────┘     │  │ HR:           $360    │    │
│                                 │  └───────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### Insights & Alerting Strategy

| Insight Category | What to Detect | Alert Severity | Action |
|---|---|---|---|
| **Agent quality** | Error rate spike by node | Warning/Critical | Check LLM API, review prompts |
| **Agent performance** | Latency p95 exceeding SLO | Warning | Scale executors, check checkpoint DB |
| **User satisfaction** | Negative feedback rate > 15% | Warning | Review traces for failing patterns |
| **Cost anomaly** | Daily spend > 120% of budget | Critical | Enforce budget guardrails, review model routing |
| **Scaling failure** | KEDA errors, replicas not matching desired | Critical | Check KEDA operator, verify scaler config |
| **Infrastructure** | CPU > 90%, OOM kills, DB connection saturation | Critical | Scale resources, right-size pods |
| **Dapr health** | Sidecar restart, state store errors | Critical | Check Dapr control plane, verify components |
| **Queue backlog** | Task queue depth growing faster than drain rate | Warning | Scale workers, investigate slow tasks |

### Alternative Observability Platforms

While the Grafana stack (Tempo + Prometheus + Loki + Grafana) is the recommended open-source approach, enterprises may choose commercial or cloud-native alternatives:

| Component | Open Source | Commercial / Cloud |
|---|---|---|
| **Traces** | Tempo, Jaeger | Datadog APM, New Relic, Dynatrace, AWS X-Ray |
| **Metrics** | Prometheus, Thanos | Datadog Metrics, CloudWatch, Azure Monitor |
| **Logs** | Loki, OpenSearch | Datadog Logs, Splunk, Elastic (ELK), CloudWatch Logs |
| **Unified UI** | Grafana | Datadog, New Relic One, Dynatrace |
| **Agent-specific** | — | LangSmith, LangFuse, Arize Phoenix |
| **Pipeline** | OTel Collector | Datadog Agent, Vector, Fluentd |

> **Recommendation:** Use **OpenTelemetry Collector** as the universal pipeline regardless of backend choice. This avoids vendor lock-in — you can switch from Tempo to Datadog (or vice versa) by changing the exporter configuration without modifying application code.

---

## Key Takeaways

1. **KEDA provides intelligent scaling** — Scale LangGraph executors based on queue depth, active runs, Prometheus metrics, or cron schedules, including scale-to-zero for cost savings.
2. **Dapr provides distributed runtime building blocks** — State management, pub/sub, service invocation, and secrets access without cloud-specific SDK code, plus automatic mTLS and trace context propagation.
3. **Together, KEDA + Dapr complete the K8s story** — KEDA handles *when/how much* to scale; Dapr handles *what each instance needs* at runtime.
4. **Capture data across four dimensions** — Agent traces, user tracking, infrastructure metrics, and application logs each serve different observability needs.
5. **Correlate with shared identifiers** — `trace_id`, `thread_id`, `run_id`, `user_id`, and `pod_name` link all four data streams.
6. **OpenTelemetry Collector is the universal pipeline** — Funnel all telemetry through OTel Collector for vendor-agnostic aggregation and routing.
7. **Grafana is the single pane of glass** — With Tempo (traces), Prometheus (metrics), and Loki (logs) as backends, Grafana provides correlated dashboarding, exploration, and alerting.

---

**Next:** [5.6 Feedback & Learning](../05-agentops.md#56-feedback--learning) | [Previous: 5.4 Making OSS LangGraph Production-Grade](05-04-langgraph-production-guide.md) | [Back to TOC](../../README.md)
