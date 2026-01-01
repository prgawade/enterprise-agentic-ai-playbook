# 4.3 Context Engineering

## Overview

Context engineering is the practice of optimizing how information is presented to language models within their context windows. Effective context engineering is critical for agent performance, as it determines what information agents can access and how efficiently they can use it.

## Understanding Context Windows

### What is a Context Window?

**Definition:** The maximum number of tokens (words/subword units) that a language model can process in a single request-response cycle.

**Key Constraints:**
- **Fixed Size:** Each model has a maximum context window (e.g., 128K tokens for Claude 3.5)
- **Shared Space:** Input and output share the same window
- **Token Limits:** Larger context = more cost and latency

### Context Window Sizes

**Typical Ranges:**
- **Small (4K-8K tokens):** Older models, efficient use cases
- **Medium (32K tokens):** Common in current models
- **Large (100K-200K tokens):** Advanced models (Claude, GPT-4)
- **Extended (1M+ tokens):** Experimental/extended models

**Impact on Agent Design:**
- Determines how much history agents can remember
- Limits document/knowledge base retrieval
- Affects multi-agent communication
- Influences planning horizon

---

## Optimizing Context Usage

### 1. Context Compression

**Purpose:** Reduce context size while preserving essential information.

#### Techniques:

**Summarization:**
```python
def compress_conversation(history: List[Message], max_tokens: int) -> str:
    # Summarize old messages
    if len(history) > max_messages:
        old_messages = history[:-max_messages]
        summary = summarize_messages(old_messages)
        recent_messages = history[-max_messages:]
        return [summary] + recent_messages
    return history
```

**Key Points Extraction:**
- Extract only key facts and decisions
- Remove redundant information
- Preserve critical context (user preferences, current goal)

**Token Optimization:**
- Remove unnecessary whitespace
- Use abbreviations where clear
- Compress structured data (JSON, XML)

#### Strategies:

**Sliding Window:**
- Keep most recent N messages
- Summarize older messages
- Progressive summarization as window fills

**Relevance Filtering:**
- Only include context relevant to current task
- Remove tangential information
- Focus on actionable context

### 2. Context Summarization

**Purpose:** Condense information into more compact representations.

#### Summarization Approaches:

**Extractive Summarization:**
- Select most important sentences/paragraphs
- Preserve original wording
- Good for factual information

**Abstractive Summarization:**
- Generate new summary text
- More compression, may lose details
- Good for narrative/historical context

**Hierarchical Summarization:**
```python
def hierarchical_summarize(messages: List[Message]) -> Summary:
    # Summarize at multiple levels
    recent_summary = summarize_recent(messages[-10:])  # Detailed
    mid_summary = summarize_mid(messages[-50:-10])     # Medium
    old_summary = summarize_old(messages[:-50])         # High-level
    
    return {
        "recent": recent_summary,
        "mid_term": mid_summary,
        "historical": old_summary
    }
```

### 3. Dynamic Context Injection

**Purpose:** Inject relevant context based on current task and user intent.

#### Context Selection:

**Relevance-Based:**
```python
def select_relevant_context(query: str, available_context: List[Context]) -> List[Context]:
    # Score contexts by relevance
    scored = []
    for ctx in available_context:
        score = relevance_score(query, ctx)
        scored.append((score, ctx))
    
    # Select top-k most relevant
    scored.sort(reverse=True)
    return [ctx for _, ctx in scored[:top_k]]
```

**Intent-Based:**
- Analyze user intent
- Select context matching intent
- Different contexts for different intents

**Task-Based:**
- Context selection based on current task type
- Data analysis → include data schemas
- Writing → include style guides and examples
- Debugging → include error logs and code context

#### RAG (Retrieval-Augmented Generation):

**Pattern:**
```
Query → Vector Search → Retrieve Relevant Docs → Inject into Context → Generate Response
```

**Implementation:**
```python
def rag_context_injection(query: str, vector_db: VectorDB) -> str:
    # Retrieve relevant documents
    relevant_docs = vector_db.semantic_search(query, top_k=5)
    
    # Format as context
    context = "\n\n".join([
        f"Document {i}:\n{doc.content}"
        for i, doc in enumerate(relevant_docs, 1)
    ])
    
    return context
```

---

## Context Management Strategies

### 1. Conversation Context

**Managing Chat History:**

**Fixed Window:**
```python
class ConversationContext:
    def __init__(self, max_messages: int = 20):
        self.messages = []
        self.max_messages = max_messages
    
    def add_message(self, message: Message):
        self.messages.append(message)
        
        # Trim if exceeds limit
        if len(self.messages) > self.max_messages:
            # Summarize oldest messages
            to_summarize = self.messages[:-self.max_messages]
            summary = self.summarize(to_summarize)
            self.messages = [summary] + self.messages[-self.max_messages:]
```

**Priority-Based:**
- Keep high-priority messages (user preferences, goals)
- Compress or remove low-priority messages (small talk)
- Weight messages by importance

### 2. Long-Term Memory Context

**Integration with Memory Systems:**

**Episodic Memory:**
- Store key events and outcomes
- Retrieve relevant past experiences
- Inject into context when relevant

**Semantic Memory:**
- Store user preferences and knowledge
- Retrieve based on current task
- Inject as background context

**Implementation:**
```python
def build_context(agent: Agent, current_goal: str) -> str:
    context_parts = []
    
    # 1. User preferences (from long-term memory)
    preferences = agent.memory.get_user_preferences()
    context_parts.append(f"User Preferences: {preferences}")
    
    # 2. Relevant past experiences
    similar_past = agent.memory.retrieve_similar_experiences(current_goal)
    if similar_past:
        context_parts.append(f"Similar Past Experiences: {similar_past}")
    
    # 3. Current conversation (compressed)
    conversation = agent.conversation.get_compressed_history()
    context_parts.append(f"Recent Conversation: {conversation}")
    
    # 4. Current goal and task context
    context_parts.append(f"Current Goal: {current_goal}")
    
    return "\n\n".join(context_parts)
```

### 3. Knowledge Base Context

**Document and Knowledge Retrieval:**

**Vector Search Integration:**
- Retrieve relevant documents for current task
- Inject as context
- Limit retrieval size to fit in context window

**Knowledge Graph Integration:**
- Query relevant entities and relationships
- Format as context
- Include relationship paths for multi-hop reasoning

---

## Context Engineering Patterns

### Pattern 1: Context Hierarchy

**Structure:**
- **System Context:** Agent role, capabilities, constraints (always included)
- **Session Context:** Current goal, recent actions (medium priority)
- **Historical Context:** Past interactions, summaries (lower priority)
- **Knowledge Context:** Retrieved documents, facts (as needed)

**Implementation:**
```python
def build_hierarchical_context(agent: Agent, goal: str) -> str:
    context = {
        "system": agent.system_prompt,
        "session": agent.get_session_context(),
        "history": agent.get_compressed_history(),
        "knowledge": agent.retrieve_knowledge(goal)
    }
    
    # Prioritize: system > session > history > knowledge
    # Allocate token budget accordingly
    return format_context(context, token_budget=agent.context_budget)
```

### Pattern 2: Progressive Context Loading

**Strategy:** Start with minimal context, load more as needed.

**Implementation:**
```python
class ProgressiveContextLoader:
    def execute(self, agent: Agent, goal: str):
        # Initial context (minimal)
        context = agent.get_minimal_context(goal)
        result = agent.execute_with_context(context)
        
        # If result indicates need for more context
        if result.requires_more_context:
            # Load additional context
            additional = agent.retrieve_additional_context(goal, result)
            context = merge_context(context, additional)
            result = agent.execute_with_context(context)
        
        return result
```

### Pattern 3: Context Templates

**Purpose:** Standardize context structure for consistency.

**Template Structure:**
```
[ROLE]
{agent_role}

[CAPABILITIES]
{available_tools}

[GOAL]
{current_goal}

[CONTEXT]
{relevant_context}

[INSTRUCTIONS]
{task_instructions}
```

**Benefits:**
- Consistent context structure
- Easier to debug and modify
- Better model understanding
- Reusable patterns

---

## Best Practices

### 1. Context Relevance

- **Principle:** Include only relevant context
- **Practice:** Filter context by relevance to current task
- **Benefit:** Better model focus, lower costs

### 2. Context Freshness

- **Principle:** Prioritize recent and relevant information
- **Practice:** Use recency weighting for context selection
- **Benefit:** Better handling of current state

### 3. Context Compression

- **Principle:** Compress when possible, detail when needed
- **Practice:** Summarize old context, keep recent detailed
- **Benefit:** More information in same token budget

### 4. Context Validation

- **Principle:** Ensure context is accurate and complete
- **Practice:** Validate retrieved context before injection
- **Benefit:** Prevent errors from bad context

### 5. Context Monitoring

- **Principle:** Track context usage and effectiveness
- **Practice:** Log context size, retrieval patterns, model responses
- **Benefit:** Optimize context engineering over time

---

## Metrics and Evaluation

### Key Metrics

**Context Efficiency:**
- Tokens used vs. tokens available
- Information density (useful info per token)
- Compression ratios

**Context Quality:**
- Relevance scores of retrieved context
- Model performance with different context strategies
- User satisfaction with agent responses

**Cost Impact:**
- Token usage reduction from compression
- API costs with different context strategies
- Infrastructure costs for context management

### Optimization Process

1. **Measure Baseline:** Current context usage and performance
2. **Identify Opportunities:** Areas for compression or improvement
3. **Implement Changes:** Apply context engineering techniques
4. **Evaluate Impact:** Measure performance and cost changes
5. **Iterate:** Refine based on results

---

**Next:** [5. AgentOps: Operations & Lifecycle Management](../../README.md#5-agentops-operations--lifecycle-management) | [Previous: 4.2 Multi-Agent Interaction Patterns](04-02-multi-agent-interaction-patterns.md) | [Back to TOC](../../README.md)

