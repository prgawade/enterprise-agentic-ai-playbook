# 2. Core Concepts & Definitions

This section establishes the foundational terminology and concepts needed to understand and build agentic AI systems.

## 2.1 Anatomy of an Agent

An AI agent is more than just a language model. It is a structured system with distinct components that enable goal-oriented behavior.

### Profile/Persona

**Definition:** The role definition and distinct capabilities that shape an agent's behavior and decision-making.

**Components:**
- **Role:** Primary function (e.g., "Data Analyst", "HR Concierge", "Security Auditor")
- **Personality:** Communication style, tone, formality level
- **Capabilities:** Tools and knowledge domains the agent can access
- **Constraints:** Boundaries and limitations of the agent's authority

**Example Persona:**
```
Role: Senior Data Analyst
Capabilities: SQL queries, statistical analysis, visualization
Personality: Professional, detail-oriented, explains methodology
Constraints: Read-only database access, no PII viewing
```

**Implementation:**
- Defined in system prompts
- Embedded in fine-tuned models
- Enforced through policy layers

### Memory

Agents require different types of memory to function effectively across time scales.

#### Short-Term Memory (Context)

**Purpose:** Maintain conversation and task context within a session

**Characteristics:**
- Limited capacity (typically 4K-128K tokens)
- Session-scoped (cleared after task completion)
- Used for immediate reasoning and decision-making

**Storage:**
- In-memory buffers
- Request context windows
- Session state management

**Use Cases:**
- Conversation history
- Current task state
- Intermediate reasoning steps

#### Long-Term Memory

**Vector Memory:**
- **Purpose:** Semantic search and retrieval of relevant information
- **Storage:** Vector databases (Pinecone, Weaviate, Qdrant)
- **Use Cases:** Knowledge base retrieval, past conversation context, domain knowledge

**Graph Memory:**
- **Purpose:** Store relationships and structured information
- **Storage:** Knowledge graphs (Neo4j, ArangoDB)
- **Use Cases:** Entity relationships, user preferences, organizational knowledge

#### Episodic Memory (Experience)

**Purpose:** Learn from past interactions and outcomes

**Characteristics:**
- Stores successful patterns
- Records failure cases for improvement
- Enables adaptation and learning

**Implementation:**
- Experience replay buffers
- Success/failure logs
- Pattern recognition from historical data

### Planning

Planning enables agents to break down complex goals into executable steps.

#### Decomposition

**Process:**
1. Receive high-level goal
2. Break into sub-tasks
3. Identify dependencies
4. Order execution sequence

**Example:**
```
Goal: "Analyze Q4 sales data and create executive summary"
Plan:
1. Query sales database for Q4 transactions
2. Calculate key metrics (revenue, growth, top products)
3. Identify trends and anomalies
4. Generate visualization charts
5. Compile executive summary document
```

#### Reasoning Patterns

**ReAct (Reasoning + Acting):**
- Interleaves reasoning steps with actions
- Allows for dynamic plan adjustment
- Improves transparency and debuggability

**Chain of Thought (CoT):**
- Step-by-step reasoning before action
- Useful for complex problem-solving
- Can improve accuracy on multi-step tasks

**Tree of Thoughts:**
- Explores multiple reasoning paths
- Evaluates alternatives before committing
- Best for high-stakes decisions

#### Reflection

**Self-Assessment:** Agents evaluate their own outputs
- Correctness checking
- Completeness verification
- Quality assessment

**Error Correction:**
- Identify failures in execution
- Analyze root causes
- Retry with improved approach

### Action Space

**Definition:** The set of available tools and APIs an agent can use to accomplish tasks.

**Tool Categories:**

1. **Data Access Tools:**
   - Database connectors (SQL, NoSQL)
   - API clients (REST, GraphQL)
   - File system access

2. **Computation Tools:**
   - Code execution environments
   - Calculator functions
   - Data processing libraries

3. **Communication Tools:**
   - Email/Slack/Teams integration
   - Notification systems
   - Calendar management

4. **External Services:**
   - Web search
   - Third-party APIs
   - Cloud service integrations

**Tool Selection:**
- Relevance to current task
- Permission and access control
- Cost and latency considerations
- Error handling capabilities

---

## 2.2 Connectivity & Standardization

Standardizing how agents access resources and communicate is critical for enterprise-scale deployments.

### Tools vs. Model Context Protocol (MCP)

#### Traditional Tool Integration

**Approach:** Custom tool definitions per framework/agent

**Challenges:**
- Framework-specific implementations
- Duplication of connectors across agents
- Inconsistent interface patterns
- Difficult to maintain and version

#### Model Context Protocol (MCP)

**Definition:** An open standard for exposing data sources and tools to AI applications in a consistent, secure manner.

**Benefits:**
- **Standardization:** Unified interface across all agents
- **Reusability:** Write once, use everywhere
- **Security:** Centralized access control
- **Versioning:** Managed resource lifecycle
- **Discovery:** Agents can discover available resources

**Components:**
- **MCP Server:** Exposes resources (databases, APIs, file systems)
- **MCP Client:** Agent runtime that connects to servers
- **Protocol:** Standardized communication format (JSON-RPC)

**Example MCP Resources:**
```json
{
  "name": "sales_database",
  "type": "database",
  "description": "Access to Q4 sales data",
  "capabilities": ["read", "query"],
  "schema": { ... }
}
```

### The Enterprise MCP Registry

**Purpose:** Centralized catalog of approved data connectors and resources available to agents.

**Components:**

1. **Resource Catalog:**
   - Available databases, APIs, file systems
   - Metadata and schemas
   - Access policies

2. **Discovery Service:**
   - Agents query registry for available resources
   - Filter by capability, domain, permission
   - Version management

3. **Security Layer:**
   - Access control policies
   - Authentication/authorization
   - Audit logging

4. **Lifecycle Management:**
   - Versioning
   - Deprecation handling
   - Migration support

**Architecture:**
```
Agent Runtime → MCP Gateway → MCP Registry → MCP Servers → Resources
```

### Agent-to-Agent (A2A) vs. MCP

#### Agent-to-Agent Communication

**Direct Communication:**
- Agents send messages directly to each other
- Custom protocols and formats
- Real-time coordination

**Use Cases:**
- Task handoffs
- Collaborative problem-solving
- Consensus building
- Multi-agent workflows

**Protocols:**
- Message passing
- Event-driven architectures
- Shared state management
- Pub/sub patterns

**Example:**
```
Researcher Agent → [Research Results] → Writer Agent
Writer Agent → [Draft Document] → Reviewer Agent
Reviewer Agent → [Feedback] → Writer Agent
```

#### MCP for Resource Access

**Indirect Communication:**
- Agents access shared resources via MCP
- Standardized resource interface
- Centralized access control

**Use Cases:**
- Shared knowledge bases
- Common data sources
- Enterprise APIs
- File systems

**Benefits:**
- Consistency
- Security
- Maintainability
- Versioning

#### Hybrid Approach

**Best Practice:** Use both patterns appropriately

- **A2A:** For coordination, handoffs, real-time collaboration
- **MCP:** For resource access, data sources, tool usage

**Example Workflow:**
```
1. Researcher Agent uses MCP to access database
2. Researcher Agent sends results via A2A to Writer Agent
3. Writer Agent uses MCP to access documentation templates
4. Writer Agent sends draft via A2A to Reviewer Agent
```

### Standardization Benefits

1. **Developer Productivity:**
   - Write connectors once
   - Reuse across agents and frameworks
   - Faster development cycles

2. **Security:**
   - Centralized access control
   - Consistent audit trails
   - Easier compliance

3. **Maintainability:**
   - Single source of truth
   - Version management
   - Easier updates

4. **Scalability:**
   - Add resources without agent changes
   - Horizontal scaling
   - Resource pooling

---

## Key Takeaways

1. **Agents are structured systems:** Profile, memory, planning, and actions work together
2. **Memory is multi-layered:** Short-term, long-term, and episodic memory serve different purposes
3. **Standardization enables scale:** MCP provides consistent resource access across agents
4. **Hybrid communication:** A2A for coordination, MCP for resources

Next: [3. The Enterprise Agent Reference Architecture](../docs/03-reference-architecture.md)

