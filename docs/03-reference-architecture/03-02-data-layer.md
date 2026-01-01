# 3.2 Data Layer

## Overview

The data layer provides persistent storage and retrieval mechanisms for agent state, knowledge, and user information. It encompasses user state management, semantic search capabilities, and structured relationship storage for complex reasoning.

## Memory Store: User State Management

### Purpose

Maintain persistent user preferences, session history, and context across interactions with agents.

### Data Types

#### 1. User Preferences

**Examples:**
- Communication style preferences
- Default parameters for agent operations
- Notification preferences
- Language and locale settings
- Trust levels for autonomous actions

**Storage Schema:**
```json
{
  "user_id": "user-12345",
  "preferences": {
    "communication_style": "concise",
    "default_language": "en-US",
    "autonomous_action_threshold": "medium",
    "notification_channels": ["email", "slack"],
    "working_hours": {
      "timezone": "America/New_York",
      "start": "09:00",
      "end": "17:00"
    }
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 2. Session History

**Purpose:** Maintain conversation context and agent interaction history

**Storage Considerations:**
- **Retention Policy:** How long to keep session data
- **Compression:** Summarize old sessions to save storage
- **Privacy:** PII handling and data retention compliance

**Schema:**
```json
{
  "session_id": "sess-12345",
  "user_id": "user-12345",
  "agent_id": "customer-support-agent",
  "started_at": "2024-01-15T10:00:00Z",
  "ended_at": "2024-01-15T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "...",
      "timestamp": "2024-01-15T10:00:05Z"
    },
    {
      "role": "assistant",
      "content": "...",
      "timestamp": "2024-01-15T10:00:10Z",
      "tool_calls": [...]
    }
  ],
  "summary": "User requested help with account setup",
  "metadata": {
    "task_completed": true,
    "satisfaction_score": 4.5
  }
}
```

#### 3. Agent Execution State

**Purpose:** Track ongoing agent tasks and their state

**Use Cases:**
- Resume interrupted tasks
- Track long-running agent operations
- Enable task cancellation
- Support task status queries

**State Machine:**
```
PENDING → RUNNING → COMPLETED
              ↓
           FAILED
              ↓
           RETRYING → RUNNING
```

### Storage Solutions

#### Relational Databases (PostgreSQL, MySQL)

**Best For:**
- Structured user preferences
- ACID transactions
- Complex queries and joins
- Strong consistency requirements

**Schema Design:**
```sql
CREATE TABLE user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    preferences JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    agent_id VARCHAR(255),
    state JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

#### Document Stores (MongoDB, DynamoDB)

**Best For:**
- Flexible schema for user preferences
- High write throughput
- Horizontal scaling
- Simple key-value lookups

**When to Use:**
- Rapidly evolving schema
- Document-based data model
- Global distribution requirements

---

## Vector Database: Semantic Search

### Purpose

Enable semantic search and retrieval for knowledge bases, enabling agents to find relevant information based on meaning rather than exact keyword matches.

### Use Cases

1. **Knowledge Retrieval:**
   - Company policies and procedures
   - Product documentation
   - Historical solutions and FAQs
   - Best practices and guidelines

2. **Context Augmentation (RAG):**
   - Inject relevant context into agent prompts
   - Improve agent responses with domain knowledge
   - Reduce hallucination through grounded retrieval

3. **Similarity Search:**
   - Find similar past interactions
   - Identify duplicate or related tasks
   - Discover relevant examples for few-shot learning

### Vector Database Options

#### Pinecone

**Characteristics:**
- Managed vector database service
- High-performance similarity search
- Automatic scaling
- Pay-per-use pricing

**Best For:**
- Quick deployment
- Managed infrastructure preference
- High-scale production workloads

#### Weaviate

**Characteristics:**
- Open-source vector database
- GraphQL API
- Built-in vectorization
- Hybrid search (vector + keyword)

**Best For:**
- Self-hosted deployments
- Custom requirements
- Graph-like data structures

#### Qdrant

**Characteristics:**
- Open-source, written in Rust
- High performance
- Filtering capabilities
- Docker deployment

**Best For:**
- Performance-critical applications
- On-premises deployments
- Cost-sensitive projects

#### Chroma

**Characteristics:**
- Lightweight, embeddable
- Python-native
- Easy to get started
- Good for development and small-scale

**Best For:**
- Development and prototyping
- Small to medium-scale deployments
- Python-heavy stack

### Data Pipeline

```
Documents → Chunking → Embedding → Vector DB
                                    ↓
                              Query → Similarity Search → Results
```

#### Embedding Generation

**Model Selection:**
- **General Purpose:** OpenAI `text-embedding-3-large`, Cohere `embed-english-v3.0`
- **Domain-Specific:** Fine-tuned models for specialized domains
- **Multilingual:** Models supporting multiple languages

**Chunking Strategies:**
- **Fixed Size:** Simple, consistent chunks
- **Semantic Chunking:** Split at semantic boundaries
- **Hierarchical:** Multiple granularities (paragraph, section, document)

#### Indexing

**Index Configuration:**
```python
# Example Pinecone Index
index_config = {
    "dimension": 1536,  # Embedding dimension
    "metric": "cosine",  # Similarity metric
    "pod_type": "p1.x1",  # Performance tier
    "replicas": 2  # High availability
}
```

### RAG Implementation Pattern

```python
# Retrieval-Augmented Generation
def retrieve_context(query: str, top_k: int = 5):
    # Generate query embedding
    query_embedding = embed_model.encode(query)
    
    # Search vector database
    results = vector_db.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    # Format context
    context = "\n\n".join([r.metadata['text'] for r in results])
    return context

def agent_query(query: str):
    # Retrieve relevant context
    context = retrieve_context(query)
    
    # Augment prompt with context
    prompt = f"""Context:
{context}

Question: {query}
Answer:"""
    
    # Generate response
    response = llm.generate(prompt)
    return response
```

### Performance Optimization

1. **Hybrid Search:** Combine vector and keyword search
2. **Filtering:** Pre-filter by metadata before vector search
3. **Caching:** Cache frequent queries
4. **Batch Operations:** Batch embedding generation and indexing

---

## Knowledge Graph: Structured Relationships

### Purpose

Store and query structured relationships between entities, enabling complex reasoning and multi-hop queries that vector search alone cannot handle.

### Use Cases

1. **Organizational Knowledge:**
   - Org chart and reporting relationships
   - Project dependencies
   - Team structures

2. **Domain Knowledge:**
   - Product hierarchies
   - Customer relationships
   - Process workflows

3. **Complex Reasoning:**
   - Multi-hop queries (A → B → C)
   - Relationship traversal
   - Pattern matching

### Graph Database Options

#### Neo4j

**Characteristics:**
- Mature, production-ready
- Cypher query language
- Rich graph algorithms
- ACID transactions

**Best For:**
- Complex relationship queries
- Enterprise deployments
- Rich graph analytics

#### Amazon Neptune

**Characteristics:**
- Managed service
- Supports Gremlin and SPARQL
- High availability
- Integration with AWS ecosystem

**Best For:**
- AWS-native deployments
- Large-scale graphs
- Managed infrastructure preference

#### ArangoDB

**Characteristics:**
- Multi-model (graph, document, key-value)
- AQL query language
- Flexible data model

**Best For:**
- Multi-model requirements
- Flexible schema needs

### Graph Schema Design

**Example: Entity-Relationship Model:**
```
(User) -[WORKS_ON]-> (Project) -[DEPENDS_ON]-> (Project)
(User) -[REPORTS_TO]-> (User)
(Project) -[BELONGS_TO]-> (Department)
```

**Neo4j Cypher Example:**
```cypher
// Find all projects a user is working on that depend on other projects
MATCH (u:User {id: 'user-123'})-[:WORKS_ON]->(p1:Project)
      -[:DEPENDS_ON]->(p2:Project)
RETURN u.name, p1.name, p2.name

// Find reporting chain
MATCH path = (u:User {id: 'user-123'})<-[:REPORTS_TO*]-(subordinate:User)
RETURN path
```

### Integration with Agents

**Pattern: Hybrid Search**
1. Use vector search for semantic similarity
2. Use knowledge graph for structured relationships
3. Combine results for comprehensive answers

**Example:**
```python
def hybrid_search(query: str):
    # Semantic search
    vector_results = vector_db.semantic_search(query)
    
    # Extract entities from query
    entities = extract_entities(query)
    
    # Graph query for relationships
    graph_results = knowledge_graph.query(
        f"MATCH (e:Entity) WHERE e.name IN {entities} RETURN e, relationships"
    )
    
    # Combine and rank results
    return combine_results(vector_results, graph_results)
```

---

## Data Governance

### Access Control

- **RBAC:** Role-based access to data stores
- **Row-Level Security:** User-specific data isolation
- **Encryption:** At-rest and in-transit encryption
- **Audit Logging:** Track all data access

### Data Quality

- **Validation:** Schema validation for structured data
- **Deduplication:** Prevent duplicate entries
- **Data Lineage:** Track data origins and transformations
- **Versioning:** Track changes to knowledge bases

### Compliance

- **GDPR:** Right to deletion, data portability
- **Retention Policies:** Automatic data expiration
- **PII Handling:** Identify and protect sensitive data
- **Audit Trails:** Comprehensive logging for compliance

---

**Next:** [3.3 Model Layer](03-03-model-layer.md) | [Previous: 3.1 Infrastructure Layer](03-01-infrastructure-layer.md) | [Back to TOC](../../README.md)

