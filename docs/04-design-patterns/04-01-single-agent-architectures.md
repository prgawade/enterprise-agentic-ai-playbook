# 4.1 Single Agent Architectures

## Overview

Single agent architectures form the foundation of agentic AI systems. Understanding how to design effective single agents—from simple single-tool agents to complex multi-tool orchestrators—is essential before moving to multi-agent systems.

## Single Tool vs. Multiple Tools

### Single Tool Agents

**Definition:** Agents that have access to only one tool or a very focused set of related tools.

**Characteristics:**
- **Simplicity:** Easier to design, build, and maintain
- **Focused Capability:** Excel at one specific task
- **Lower Cognitive Load:** Clear decision boundaries
- **Faster Development:** Rapid prototyping and deployment

**Use Cases:**
- **Database Query Agent:** Only tool is database query interface
- **Email Agent:** Only tool is email API (send, read, search)
- **Calendar Agent:** Only tool is calendar API (create, read, update events)
- **Search Agent:** Only tool is search API

**Design Pattern:**
```python
class SingleToolAgent:
    def __init__(self, tool: Tool, llm: LanguageModel):
        self.tool = tool
        self.llm = llm
    
    def execute(self, goal: str) -> Result:
        # LLM determines how to use the single tool
        plan = self.llm.plan(goal, available_tools=[self.tool])
        
        # Execute tool calls
        results = []
        for action in plan.actions:
            result = self.tool.execute(action.parameters)
            results.append(result)
        
        # Synthesize results
        return self.llm.synthesize(goal, results)
```

**Advantages:**
- ✅ Clear purpose and boundaries
- ✅ Easier to test and validate
- ✅ Lower complexity
- ✅ Faster execution (no tool selection overhead)

**Limitations:**
- ❌ Limited to one domain
- ❌ Cannot handle complex, multi-system workflows
- ❌ May require multiple agents for complex tasks

---

### Multiple Tools Agents

**Definition:** Agents that have access to multiple, potentially diverse tools.

**Characteristics:**
- **Versatility:** Can handle complex, multi-step tasks
- **System Integration:** Coordinate across multiple systems
- **Higher Complexity:** More decision points and potential failure modes
- **Cognitive Load:** Must choose appropriate tools from a larger set

**Use Cases:**
- **Customer Support Agent:** Email, CRM, knowledge base, calendar tools
- **Data Analyst Agent:** Database, visualization, file system, reporting tools
- **Project Manager Agent:** Task management, communication, document, calendar tools

**Design Pattern:**
```python
class MultiToolAgent:
    def __init__(self, tools: List[Tool], llm: LanguageModel):
        self.tools = {tool.name: tool for tool in tools}
        self.llm = llm
    
    def execute(self, goal: str) -> Result:
        # LLM selects and sequences tools
        plan = self.llm.plan(
            goal, 
            available_tools=list(self.tools.values()),
            tool_descriptions=self.get_tool_descriptions()
        )
        
        # Execute tool calls
        results = []
        for action in plan.actions:
            tool = self.tools[action.tool_name]
            result = tool.execute(action.parameters)
            results.append(result)
            
            # Optionally replan based on intermediate results
            if self.should_replan(results, goal):
                plan = self.llm.replan(goal, results, plan)
        
        return self.llm.synthesize(goal, results)
```

**Tool Selection Strategies:**

**1. LLM-Based Selection:**
- LLM chooses tools based on natural language descriptions
- Flexible and adaptable
- Can handle ambiguous requests
- May select wrong tool

**2. Rule-Based Selection:**
- Explicit rules for tool selection
- Deterministic and predictable
- Requires maintenance
- Limited flexibility

**3. Hybrid Approach:**
- Rules for common patterns
- LLM for complex or ambiguous cases
- Balances reliability and flexibility

**Advantages:**
- ✅ Handle complex, multi-system workflows
- ✅ Versatile and adaptable
- ✅ Single agent for diverse tasks
- ✅ Better user experience (one agent, many capabilities)

**Limitations:**
- ❌ Higher complexity
- ❌ Tool selection errors
- ❌ Increased latency (tool selection overhead)
- ❌ More difficult to debug

---

### Managing Cognitive Load

**Challenge:** As the number of tools increases, the agent must manage more complexity in tool selection and orchestration.

**Strategies:**

#### 1. Tool Organization

**Categorization:**
```python
tools = {
    "communication": [email_tool, slack_tool, sms_tool],
    "data": [database_tool, file_system_tool, api_tool],
    "automation": [workflow_tool, scheduler_tool]
}
```

**Hierarchical Selection:**
- First select category
- Then select tool within category
- Reduces search space

#### 2. Tool Descriptions

**Clear, Descriptive Names:**
```python
# Good
"send_email": "Sends an email message to specified recipients"

# Bad
"mail": "Email tool"
```

**Rich Metadata:**
```python
{
    "name": "query_database",
    "description": "Execute SQL queries against the sales database",
    "category": "data",
    "use_cases": ["data_retrieval", "analytics"],
    "examples": ["Get sales for Q4", "List top customers"]
}
```

#### 3. Tool Usage Patterns

**Learning from Experience:**
- Track which tools are used together
- Suggest common tool combinations
- Learn from successful executions

#### 4. Tool Limits

**Guidelines:**
- Limit to 10-20 tools for single agents
- Split into multiple agents if more tools needed
- Use tool hierarchies for organization

---

## Branching Logic

### Deterministic Branching

**Definition:** Conditional logic based on explicit rules and deterministic conditions.

**Characteristics:**
- **Predictable:** Same inputs produce same path
- **Testable:** Easy to unit test
- **Maintainable:** Clear logic flow
- **Limited Flexibility:** Cannot handle ambiguous cases

**Implementation:**
```python
class DeterministicAgent:
    def execute(self, goal: str) -> Result:
        # Deterministic branching
        if self.is_data_query(goal):
            return self.handle_data_query(goal)
        elif self.is_communication_task(goal):
            return self.handle_communication(goal)
        elif self.is_automation_task(goal):
            return self.handle_automation(goal)
        else:
            return self.handle_default(goal)
    
    def is_data_query(self, goal: str) -> bool:
        keywords = ["query", "retrieve", "get data", "analyze"]
        return any(keyword in goal.lower() for keyword in keywords)
```

**Use Cases:**
- Well-defined workflows
- Compliance-driven processes
- High-reliability requirements
- Simple conditional logic

**Advantages:**
- ✅ Predictable behavior
- ✅ Easy to test and validate
- ✅ Clear audit trails
- ✅ High reliability

**Limitations:**
- ❌ Inflexible
- ❌ Cannot handle ambiguity
- ❌ Requires explicit rules for all cases

---

### Probabilistic Branching

**Definition:** Conditional logic driven by LLM reasoning, which may produce different paths for similar inputs.

**Characteristics:**
- **Adaptive:** Handles ambiguous and novel situations
- **Context-Aware:** Considers full context in decisions
- **Unpredictable:** Same inputs may take different paths
- **Complex:** Harder to test and validate

**Implementation:**
```python
class ProbabilisticAgent:
    def execute(self, goal: str) -> Result:
        # LLM decides on execution path
        decision = self.llm.decide_path(
            goal=goal,
            context=self.get_context(),
            available_tools=self.tools,
            previous_actions=self.action_history
        )
        
        # Execute chosen path
        if decision.path == "data_analysis":
            return self.execute_data_analysis(goal, decision.parameters)
        elif decision.path == "communication":
            return self.execute_communication(goal, decision.parameters)
        else:
            return self.execute_custom_path(decision)
```

**Decision Factors:**
- Goal interpretation
- Available context
- Historical patterns
- Tool availability
- User preferences

**Use Cases:**
- Ambiguous user requests
- Novel situations
- Complex decision-making
- User-facing agents

**Advantages:**
- ✅ Flexible and adaptive
- ✅ Handles ambiguity
- ✅ Context-aware decisions
- ✅ Natural language understanding

**Limitations:**
- ❌ Unpredictable behavior
- ❌ Harder to test
- ❌ May make suboptimal decisions
- ❌ Requires fallback mechanisms

---

### Hybrid Approaches

**Pattern:** Combine deterministic rules for known patterns with probabilistic reasoning for ambiguous cases.

**Implementation:**
```python
class HybridAgent:
    def execute(self, goal: str) -> Result:
        # Try deterministic rules first
        if self.has_deterministic_rule(goal):
            return self.execute_deterministic(goal)
        
        # Fall back to probabilistic
        return self.execute_probabilistic(goal)
    
    def has_deterministic_rule(self, goal: str) -> bool:
        # Check against known patterns
        patterns = self.load_known_patterns()
        return self.matches_pattern(goal, patterns)
```

**Benefits:**
- Reliability of deterministic logic
- Flexibility of probabilistic reasoning
- Best of both worlds

**Use Cases:**
- Production systems requiring reliability
- Systems with known common patterns
- Systems needing to handle novel cases

---

## Architecture Patterns

### Pattern 1: Simple Sequential Agent

**Structure:**
```
Goal → Plan → Execute Tools (Sequential) → Synthesize → Result
```

**Characteristics:**
- Linear execution
- No branching or loops
- Simple to implement
- Limited adaptability

**Example:**
```python
class SequentialAgent:
    def execute(self, goal: str):
        plan = self.create_plan(goal)
        results = []
        for step in plan.steps:
            result = self.execute_step(step)
            results.append(result)
        return self.synthesize(results)
```

---

### Pattern 2: Loop-Based Agent

**Structure:**
```
Goal → Plan → Execute → Evaluate → [Loop if incomplete] → Result
```

**Characteristics:**
- Iterative execution
- Can adapt based on results
- More complex than sequential
- Better for uncertain outcomes

**Example:**
```python
class LoopBasedAgent:
    def execute(self, goal: str):
        plan = self.create_initial_plan(goal)
        max_iterations = 10
        
        for iteration in range(max_iterations):
            results = self.execute_plan(plan)
            
            if self.is_complete(results, goal):
                return self.synthesize(results)
            
            # Replan based on results
            plan = self.replan(goal, results, plan)
        
        raise MaxIterationsExceeded()
```

---

### Pattern 3: State Machine Agent

**Structure:**
```
States: IDLE → PLANNING → EXECUTING → EVALUATING → [Loop or COMPLETE]
```

**Characteristics:**
- Explicit state management
- Clear state transitions
- Easy to monitor and debug
- More structured than loops

**Example:**
```python
class StateMachineAgent:
    def __init__(self):
        self.state = AgentState.IDLE
    
    def execute(self, goal: str):
        self.state = AgentState.PLANNING
        plan = self.plan(goal)
        
        self.state = AgentState.EXECUTING
        results = self.execute_plan(plan)
        
        while self.state == AgentState.EXECUTING:
            self.state = AgentState.EVALUATING
            if self.is_complete(results, goal):
                self.state = AgentState.COMPLETE
                return self.synthesize(results)
            
            self.state = AgentState.PLANNING
            plan = self.replan(goal, results, plan)
            
            self.state = AgentState.EXECUTING
            results = self.execute_plan(plan)
```

---

## Best Practices

### 1. Start Simple

- Begin with single-tool agents
- Add complexity gradually
- Validate each increment

### 2. Clear Tool Boundaries

- Well-defined tool responsibilities
- Minimal tool overlap
- Clear tool descriptions

### 3. Error Handling

- Graceful degradation
- Clear error messages
- Retry mechanisms
- Fallback strategies

### 4. Observability

- Log all tool calls
- Track decision points
- Monitor performance
- Debug-friendly architecture

### 5. Testing

- Unit tests for deterministic logic
- Integration tests for tool interactions
- E2E tests for full workflows
- Probabilistic testing for LLM decisions

---

**Next:** [4.2 Multi-Agent Interaction Patterns](04-02-multi-agent-interaction-patterns.md) | [Back to TOC](../../README.md)

