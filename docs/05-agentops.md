# 5. AgentOps: Operations & Lifecycle Management

This section covers the frameworks, tools, and practices for developing, deploying, and managing agentic AI systems in production.

## 5.1 Development Frameworks

Selecting the right framework is critical for building maintainable and scalable agent systems.

### LangGraph

**Overview:** Graph-based state management and cyclic flows for building stateful, multi-actor applications

**Key Features:**
- **State Graphs:** Visual representation of agent workflows
- **Cyclic Flows:** Support for loops and iterative processes
- **State Management:** Built-in state persistence and checkpointing
- **Human-in-the-Loop:** Built-in interruption and approval mechanisms

**Architecture:**
```python
from langgraph.graph import StateGraph

workflow = StateGraph(State)

# Add nodes (agents/tools)
workflow.add_node("researcher", research_agent)
workflow.add_node("writer", writer_agent)
workflow.add_node("reviewer", reviewer_agent)

# Define edges (flows)
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "reviewer")
workflow.add_conditional_edges("reviewer", should_continue)

# Compile and run
app = workflow.compile()
```

**Use Cases:**
- Multi-step workflows with complex state
- ReAct-style agents with reasoning loops
- Multi-agent coordination
- Workflows requiring cycles and iteration

**Advantages:**
- Intuitive graph-based modeling
- Built-in state management
- Strong debugging capabilities
- Production-ready features (checkpointing, streaming)

**Considerations:**
- Python-first (other languages less mature)
- Learning curve for graph-based thinking
- Requires understanding of state management

### Microsoft Semantic Kernel & AutoGen

**Overview:** Enterprise-grade orchestration frameworks from Microsoft

#### Semantic Kernel

**Features:**
- **Planner:** Automatic plan generation from natural language
- **Plugins:** Modular tool/function system
- **Memory:** Integrated vector memory
- **Multi-LLM:** Support for multiple model providers

**Architecture:**
```csharp
var kernel = Kernel.CreateBuilder()
    .AddOpenAIChatCompletion(...)
    .Build();

var planner = new FunctionCallingStepwisePlanner(kernel);
var plan = planner.CreatePlan("Analyze sales data and generate report");
var result = await plan.InvokeAsync(kernel);
```

**Use Cases:**
- Enterprise .NET/C# environments
- Automatic workflow generation
- Plugin-based architectures
- Multi-model deployments

#### AutoGen

**Features:**
- **Multi-Agent Systems:** Built-in support for agent teams
- **Conversation Patterns:** Pre-built interaction patterns
- **Code Execution:** Built-in code execution capabilities
- **Flexible Orchestration:** Various coordination patterns

**Architecture:**
```python
# Create agents
assistant = ConversableAgent("assistant", llm_config={...})
user_proxy = ConversableAgent("user_proxy", code_execution_config={...})

# Initiate conversation
user_proxy.initiate_chat(assistant, message="Solve this problem...")
```

**Use Cases:**
- Multi-agent conversations
- Code generation and execution
- Collaborative problem-solving
- Research and analysis workflows

**Advantages:**
- Enterprise support and documentation
- Production-ready features
- Strong Microsoft ecosystem integration
- Active development and community

**Considerations:**
- Primarily Microsoft ecosystem
- Learning curve for complex scenarios
- More opinionated frameworks

### Strands Agents / Custom SDKs

**Overview:** Various specialized frameworks and custom development approaches

#### Framework Selection Criteria

**Considerations:**

1. **Language Support:**
   - Python: LangGraph, LangChain, AutoGen
   - JavaScript/TypeScript: LangChain.js, Vercel AI SDK
   - C#/.NET: Semantic Kernel
   - Java: LangChain4j

2. **Complexity Needs:**
   - Simple workflows: LangChain, basic frameworks
   - Complex state: LangGraph, Temporal
   - Multi-agent: AutoGen, CrewAI
   - Custom needs: Build custom SDK

3. **Production Requirements:**
   - Observability: Frameworks with built-in logging
   - Scalability: Support for distributed execution
   - Reliability: Checkpointing, retries, error handling
   - Security: Built-in security features

4. **Ecosystem Integration:**
   - Cloud provider alignment
   - Existing tooling compatibility
   - Team expertise
   - Community and support

**Decision Matrix:**

| Framework | Best For | Language | Complexity |
|-----------|----------|----------|------------|
| LangGraph | Complex stateful workflows | Python | High |
| LangChain | Quick prototyping, chains | Python/JS | Medium |
| Semantic Kernel | Enterprise .NET | C# | Medium |
| AutoGen | Multi-agent systems | Python | High |
| Custom SDK | Unique requirements | Any | Variable |

#### Custom SDK Development

**When to Build Custom:**
- Unique architectural requirements
- Tight integration with existing systems
- Performance-critical applications
- Specialized domain needs

**Key Components:**
- Agent runtime engine
- State management
- Tool/function system
- LLM abstraction layer
- Observability hooks

---

## 5.2 MCP Development

Building and managing Model Context Protocol servers for standardized resource access.

### MCP Templates

**Purpose:** Standardize how internal APIs are exposed to agents

**Template Structure:**
```json
{
  "name": "database_mcp_server",
  "version": "1.0.0",
  "resources": [
    {
      "name": "sales_data",
      "type": "database_table",
      "description": "Access to sales transactions",
      "schema": {
        "table": "sales",
        "columns": ["id", "date", "amount", "product_id"]
      },
      "capabilities": ["read", "query"]
    }
  ],
  "tools": [
    {
      "name": "query_sales",
      "description": "Execute SQL query on sales data",
      "parameters": {
        "sql": "string"
      }
    }
  ]
}
```

**Template Categories:**

1. **Database Connectors:**
   - SQL databases (PostgreSQL, MySQL)
   - NoSQL databases (MongoDB, DynamoDB)
   - Data warehouses (Snowflake, BigQuery)

2. **API Connectors:**
   - REST APIs
   - GraphQL endpoints
   - Internal microservices

3. **File System Connectors:**
   - Local file systems
   - Cloud storage (S3, Blob Storage)
   - Version control (Git)

4. **Application Connectors:**
   - CRM systems (Salesforce)
   - ERP systems
   - Collaboration tools (Slack, Teams)

**Standardization Benefits:**
- Consistent interface patterns
- Reusable templates
- Easier agent development
- Simplified testing

### Server Implementation

**Building Secure MCP Servers:**

#### Architecture

```
Agent Runtime → MCP Client → MCP Server → Resource (Database/API/File System)
                ↓
            Security Layer
                ↓
            Access Control
```

#### Implementation Steps

1. **Define Resource Schema:**
   - Document available resources
   - Specify capabilities and permissions
   - Define data models

2. **Implement Server:**
   ```python
   from mcp.server import Server
   from mcp.types import Resource, Tool
   
   server = Server("database_server")
   
   @server.resource("sales_data")
   async def get_sales_data(uri: str) -> bytes:
       # Query database
       # Return data
       pass
   
   @server.tool("query_sales")
   async def query_sales(sql: str) -> dict:
       # Validate SQL
       # Execute query
       # Return results
       pass
   ```

3. **Security Implementation:**
   - Authentication (API keys, OAuth)
   - Authorization (RBAC, attribute-based)
   - Input validation
   - SQL injection prevention
   - Rate limiting

4. **Error Handling:**
   - Graceful error responses
   - Detailed error logging
   - Retry mechanisms
   - Circuit breakers

#### Security Best Practices

**Authentication:**
- Service account credentials
- API key rotation
- OAuth 2.0 for user context
- mTLS for service-to-service

**Authorization:**
- Principle of least privilege
- Row-level security for databases
- Resource-level permissions
- Audit logging

**Input Validation:**
- Schema validation
- SQL injection prevention (parameterized queries)
- Path traversal prevention
- Size limits

**Example Secure Implementation:**
```python
@server.tool("query_sales")
async def query_sales(sql: str, user_context: UserContext) -> dict:
    # 1. Authenticate
    if not authenticate(user_context):
        raise AuthenticationError
    
    # 2. Authorize
    if not authorize(user_context, "sales_data", "read"):
        raise AuthorizationError
    
    # 3. Validate SQL (whitelist, syntax check)
    if not validate_sql(sql, allowed_operations=["SELECT"]):
        raise ValidationError("Only SELECT queries allowed")
    
    # 4. Execute with parameterized query
    results = execute_parameterized_query(sql)
    
    # 5. Audit log
    audit_log(user_context, "query_sales", sql)
    
    return results
```

---

## 5.3 Agent Templates

**Purpose:** Reusable blueprints for common agent types

### Template Categories

#### The Data Analyst

**Capabilities:**
- SQL query generation and execution
- Statistical analysis
- Data visualization
- Report generation

**Tools:**
- Database connectors
- Analysis libraries (pandas, numpy)
- Visualization tools (matplotlib, plotly)
- Report generators

**Persona:**
- Analytical and precise
- Explains methodology
- Data-driven insights
- Professional tone

**Template Structure:**
```yaml
name: data_analyst
persona: |
  You are a senior data analyst with expertise in SQL, statistics, 
  and data visualization. You explain your methodology clearly.
tools:
  - query_database
  - calculate_statistics
  - generate_chart
  - create_report
memory:
  - user_preferences
  - past_queries
  - analysis_patterns
```

#### The HR Concierge

**Capabilities:**
- Employee information lookup
- Leave request processing
- Policy explanations
- Benefits queries

**Tools:**
- HRIS integration
- Calendar systems
- Document retrieval
- Communication tools

**Persona:**
- Friendly and helpful
- Confidential and professional
- Clear communicator

#### The Security Auditor

**Capabilities:**
- Security policy verification
- Access review
- Compliance checking
- Threat analysis

**Tools:**
- Security information systems
- Audit logs
- Policy databases
- Risk assessment tools

**Persona:**
- Thorough and detail-oriented
- Security-focused
- Compliance-aware

### Template Development

**Process:**
1. **Identify Patterns:** Common agent use cases
2. **Define Capabilities:** Tools and knowledge required
3. **Create Persona:** Role definition and communication style
4. **Document Examples:** Sample interactions
5. **Version Control:** Template versioning and updates

**Template Repository:**
- Centralized template library
- Version management
- Community contributions
- Testing and validation

**Customization:**
- Extend base templates
- Add domain-specific tools
- Customize personas
- Configure memory strategies

---

## 5.4 Feedback & Learning

Enabling agents to improve through human feedback and automated learning mechanisms.

### Human-in-the-Loop (HITL)

**Purpose:** Inject human judgment into agent workflows

#### Approval Gates

**Implementation:**
- Pause agent execution at decision points
- Present options to human reviewer
- Wait for approval before proceeding
- Log decisions for learning

**Use Cases:**
- High-stakes decisions
- Policy-sensitive actions
- Creative outputs requiring review
- Cost-sensitive operations

**Example:**
```
Agent: "I've generated a marketing email. Should I send it?"
System: [Pause] → Present email to reviewer
Human: Approve/Reject/Edit
Agent: Continue based on decision
```

#### Correction Interfaces

**Design Principles:**
- Clear presentation of agent output
- Easy editing/correction mechanisms
- Feedback capture
- Learning integration

**Interface Types:**
- **Inline Editing:** Edit agent output directly
- **Feedback Forms:** Structured feedback collection
- **Conversational:** Natural language corrections
- **Annotation:** Mark errors/suggestions

**Feedback Collection:**
- What was wrong?
- What should it have been?
- Why did the error occur?
- How to prevent it?

#### HITL Patterns

**Pattern 1: Pre-Execution Approval**
```
Agent Plan → Human Review → Approval → Execution
```

**Pattern 2: Post-Execution Review**
```
Execution → Output → Human Review → Correction → Update
```

**Pattern 3: Continuous Monitoring**
```
Execution → Monitoring → Alert on Anomaly → Human Intervention
```

**Pattern 4: Confidence-Based**
```
Execution → Low Confidence → Escalate to Human
         → High Confidence → Proceed Automatically
```

### Reinforcement Learning from Human Feedback (RLHF)

**Purpose:** Fine-tune models on agent-specific trajectories

#### Process

1. **Data Collection:**
   - Collect agent execution trajectories
   - Human ratings of outputs
   - Success/failure signals
   - Comparative rankings

2. **Reward Modeling:**
   - Train reward model on human preferences
   - Predict human ratings
   - Generate reward signals

3. **Policy Optimization:**
   - Fine-tune base model using rewards
   - Improve agent behavior
   - Optimize for specific tasks

4. **Iteration:**
   - Deploy improved model
   - Collect new data
   - Continue refinement

#### Implementation Considerations

**Challenges:**
- Expensive human labeling
- Reward model accuracy
- Distribution shift
- Evaluation metrics

**Best Practices:**
- Start with strong base models
- Focus on high-impact behaviors
- Use comparative feedback (A/B)
- Iterate incrementally

### Self-Correction Loops

**Purpose:** Agents analyze their own errors and retry with improved approaches

#### Error Detection

**Types of Errors:**
- Tool execution failures
- Invalid outputs
- User feedback (negative)
- Validation failures
- Timeout errors

**Detection Mechanisms:**
- Return code checking
- Output validation
- User signal interpretation
- External validators
- Confidence thresholds

#### Correction Strategies

**Strategy 1: Retry with Variation**
```
Error → Analyze cause → Modify approach → Retry
```

**Strategy 2: Alternative Path**
```
Error → Identify alternative → Switch approach → Execute
```

**Strategy 3: Decomposition**
```
Error → Break into smaller steps → Execute step-by-step
```

**Strategy 4: External Help**
```
Error → Request clarification → Update understanding → Retry
```

#### Implementation Example

```python
def agent_execution_with_correction(task):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = execute_task(task)
            if validate_result(result):
                return result
            else:
                error = analyze_error(result)
                task = apply_correction(task, error)
        except Exception as e:
            error = analyze_exception(e)
            task = apply_correction(task, error)
    
    # Escalate to human if all retries fail
    return escalate_to_human(task)
```

#### Learning from Corrections

**Pattern Recognition:**
- Identify common error patterns
- Learn correction strategies
- Build error-correction knowledge base
- Improve over time

**Feedback Integration:**
- Log corrections
- Update agent knowledge
- Refine prompts
- Improve validation

---

## Key Takeaways

1. **Framework selection:** Match framework to use case and team capabilities
2. **MCP standardization:** Build reusable, secure MCP servers
3. **Template reuse:** Leverage agent templates for common patterns
4. **Continuous improvement:** Implement feedback loops for learning
5. **Human oversight:** Strategic HITL integration for quality and safety

Next: [6. Evaluation & Reliability](../docs/06-evaluation-reliability.md)

