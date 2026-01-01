# 4.2 Multi-Agent Interaction Patterns

## Overview

Multi-agent systems enable complex problem-solving through specialization and collaboration. Understanding different interaction patterns is crucial for designing effective multi-agent architectures that balance coordination overhead with capability gains.

## Centralized (Supervisor/Boss)

### Architecture

**Pattern:** Hub-and-spoke model where a supervisor agent delegates tasks to specialized worker agents.

```
              ┌─────────────┐
              │ Supervisor  │
              │   Agent     │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
    ┌───▼───┐   ┌───▼───┐   ┌───▼───┐
    │Worker │   │Worker │   │Worker │
    │Agent A│   │Agent B│   │Agent C│
    └───────┘   └───────┘   └───────┘
```

**Characteristics:**
- **Single Point of Control:** Supervisor coordinates all activity
- **Task Delegation:** Supervisor breaks down work and assigns to workers
- **Result Aggregation:** Supervisor collects and synthesizes results
- **Centralized Decision-Making:** Supervisor makes high-level decisions

### Supervisor Responsibilities

**1. Task Decomposition:**
- Break down high-level goals into sub-tasks
- Identify required capabilities
- Determine task dependencies

**2. Agent Selection:**
- Choose appropriate worker agent for each task
- Consider agent capabilities and availability
- Balance workload across agents

**3. Coordination:**
- Manage task execution order
- Handle dependencies between tasks
- Coordinate parallel execution

**4. Result Synthesis:**
- Aggregate worker agent results
- Resolve conflicts or inconsistencies
- Generate final output

**Implementation:**
```python
class SupervisorAgent:
    def __init__(self, worker_agents: List[Agent]):
        self.workers = {agent.role: agent for agent in worker_agents}
    
    def execute(self, goal: str) -> Result:
        # Decompose goal
        tasks = self.decompose_goal(goal)
        
        # Assign tasks to workers
        assignments = self.assign_tasks(tasks)
        
        # Execute tasks (parallel where possible)
        results = {}
        for task_id, (task, worker) in assignments.items():
            results[task_id] = worker.execute(task)
        
        # Synthesize results
        return self.synthesize_results(goal, results)
    
    def assign_tasks(self, tasks: List[Task]) -> Dict[str, Tuple[Task, Agent]]:
        assignments = {}
        for task in tasks:
            # Select best worker for task
            worker = self.select_worker(task)
            assignments[task.id] = (task, worker)
        return assignments
```

### Use Cases

**Advantages:**
- ✅ Clear hierarchy and control
- ✅ Easier to debug and monitor
- ✅ Simple coordination logic
- ✅ Good for hierarchical organizations

**Disadvantages:**
- ❌ Single point of failure (supervisor)
- ❌ Potential bottleneck
- ❌ Less flexibility for worker autonomy
- ❌ Supervisor complexity grows with system size

**Best For:**
- Well-defined workflows with clear task boundaries
- Hierarchical organizational structures
- Systems requiring strong centralized control
- When task dependencies are complex

**Examples:**
- Customer service: Supervisor routes to specialist agents
- Content creation: Supervisor coordinates writer, editor, reviewer
- Data analysis: Supervisor orchestrates data collection, analysis, reporting

---

## Sequential (Handoffs)

### Architecture

**Pattern:** Assembly line processing where agents pass work sequentially, each adding value before handing off to the next agent.

```
    ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐
    │Agent │ ──→ │Agent │ ──→ │Agent │ ──→ │Agent │
    │  A   │     │  B   │     │  C   │     │  D   │
    └──────┘     └──────┘     └──────┘     └──────┘
   Research    →  Analyze  →  Write   →  Review
```

**Characteristics:**
- **Linear Flow:** Tasks flow in a single direction
- **Specialized Stages:** Each agent specializes in one stage
- **Incremental Value:** Each stage adds value to the output
- **Clear Handoff Points:** Well-defined interfaces between stages

### Implementation

**Pattern:**
```python
class SequentialAgentSystem:
    def __init__(self, agents: List[Agent]):
        self.agents = agents  # Ordered list
    
    def execute(self, initial_input: Any) -> Result:
        current_data = initial_input
        
        for agent in self.agents:
            # Agent processes current data
            current_data = agent.process(current_data)
            
            # Optional: validate before handoff
            if not self.validate_handoff(current_data, agent):
                raise HandoffValidationError()
        
        return current_data  # Final result
```

**Handoff Validation:**
```python
def validate_handoff(self, data: Any, from_agent: Agent) -> bool:
    # Check data format
    if not self.check_format(data, from_agent.output_schema):
        return False
    
    # Check data quality
    if not self.check_quality(data, from_agent.quality_metrics):
        return False
    
    return True
```

### Use Cases

**Advantages:**
- ✅ Simple, linear flow
- ✅ Clear stage boundaries
- ✅ Easy to understand and debug
- ✅ Natural fit for pipeline workflows

**Disadvantages:**
- ❌ Sequential bottleneck (no parallelism)
- ❌ No feedback loops
- ❌ Difficult to skip or reorder stages
- ❌ One failure can block entire pipeline

**Best For:**
- Content creation pipelines (research → write → edit → publish)
- Data processing pipelines (extract → transform → load)
- Approval workflows (submit → review → approve)
- Manufacturing-like processes

**Examples:**
- **Document Creation:** Researcher → Writer → Editor → Publisher
- **Code Review:** Developer → Linter → Reviewer → Approver
- **Data Pipeline:** Extractor → Validator → Transformer → Loader

---

## Hierarchical

### Architecture

**Pattern:** Teams of teams—manager agents oversee groups of worker agents, forming multiple levels of hierarchy.

```
                    ┌─────────────┐
                    │   Top-Level │
                    │   Manager   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼────┐  ┌──────▼────┐  ┌─────▼─────┐
    │   Manager  │  │  Manager  │  │  Manager  │
    │  (Team A)  │  │ (Team B)  │  │ (Team C)  │
    └──────┬─────┘  └─────┬─────┘  └─────┬─────┘
           │              │              │
    ┌──────┼──────┐ ┌─────┼─────┐ ┌──────┼──────┐
    │      │      │ │     │     │ │      │      │
 ┌──▼──┐ ┌─▼──┐ ┌─▼─┐ ┌──▼──┐ ┌─▼─┐ ┌──▼──┐ ┌──▼──┐
 │Worker│ │Wkr │ │Wkr│ │Wkr  │ │Wkr│ │Wkr  │ │Wkr  │
 └──────┘ └────┘ └───┘ └─────┘ └───┘ └─────┘ └─────┘
```

**Characteristics:**
- **Multi-Level Management:** Multiple layers of coordination
- **Scalability:** Can handle large numbers of agents
- **Specialization:** Each level has distinct responsibilities
- **Distributed Control:** Control distributed across levels

### Implementation

```python
class HierarchicalAgentSystem:
    def __init__(self, root_manager: ManagerAgent):
        self.root = root_manager
    
    def execute(self, goal: str) -> Result:
        # Top-level manager decomposes goal
        sub_goals = self.root.decompose(goal)
        
        # Assign to mid-level managers
        results = {}
        for sub_goal, manager in self.root.assign_sub_goals(sub_goals):
            # Manager further decomposes and assigns to workers
            result = manager.execute(sub_goal)
            results[sub_goal.id] = result
        
        # Aggregate results
        return self.root.synthesize(results)
```

### Management Levels

**Top-Level Manager:**
- Strategic planning
- High-level goal decomposition
- Coordination between teams
- Final result synthesis

**Mid-Level Managers:**
- Tactical planning
- Task assignment to workers
- Team coordination
- Quality assurance

**Workers:**
- Task execution
- Specialized work
- Result generation
- Status reporting

### Use Cases

**Advantages:**
- ✅ Scales to large numbers of agents
- ✅ Clear organizational structure
- ✅ Distributed decision-making
- ✅ Natural fit for enterprise organizations

**Disadvantages:**
- ❌ Complex coordination logic
- ❌ Communication overhead between levels
- ❌ Potential bottlenecks at management levels
- ❌ Difficult to debug across levels

**Best For:**
- Large-scale systems with many agents
- Enterprise organizations with multiple departments
- Complex projects requiring multiple teams
- Systems needing both strategic and tactical coordination

**Examples:**
- **Enterprise Project:** CEO → Department Heads → Team Leads → Individual Contributors
- **Software Development:** Product Manager → Engineering Managers → Team Leads → Developers
- **Research Organization:** Research Director → Lab Managers → Principal Investigators → Researchers

---

## Joint Collaboration

### Architecture

**Pattern:** Roundtable discussions/debates where agents collaborate through conversation to reach consensus or generate solutions.

```
        ┌──────────┐
        │  Agent A │
        └────┬─────┘
             │
    ┌────────┼────────┐
    │        │        │
┌───▼───┐ ┌─▼────┐ ┌─▼────┐
│Agent B│ │Agent │ │Agent │
│       │ │  C   │ │  D   │
└───▲───┘ └─▲────┘ └─▲────┘
    │        │        │
    └────────┼────────┘
             │
        ┌────▼─────┐
        │Consensus │
        │ Mechanism│
        └──────────┘
```

**Characteristics:**
- **Peer-to-Peer:** No central coordinator (or minimal coordinator)
- **Iterative Discussion:** Agents exchange ideas and refine solutions
- **Consensus Building:** Agents work toward agreement
- **Emergent Solutions:** Solutions emerge from interaction

### Collaboration Mechanisms

#### 1. Debate Pattern

**Process:**
- Agents present different perspectives
- Agents critique and refine proposals
- Iterate until consensus or time limit

**Implementation:**
```python
class DebateCollaboration:
    def collaborate(self, agents: List[Agent], topic: str) -> Result:
        proposals = {}
        
        # Initial proposals
        for agent in agents:
            proposals[agent.id] = agent.propose(topic)
        
        # Debate rounds
        for round_num in range(self.max_rounds):
            critiques = {}
            for agent in agents:
                critiques[agent.id] = agent.critique(proposals, topic)
            
            # Refine proposals
            for agent in agents:
                proposals[agent.id] = agent.refine(
                    proposals[agent.id],
                    critiques
                )
            
            # Check for consensus
            if self.has_consensus(proposals):
                return self.synthesize_consensus(proposals)
        
        # Return best proposal if no consensus
        return self.select_best(proposals)
```

#### 2. Brainstorming Pattern

**Process:**
- Agents generate ideas independently
- Agents build on each other's ideas
- Aggregate and synthesize ideas

**Implementation:**
```python
class BrainstormingCollaboration:
    def collaborate(self, agents: List[Agent], prompt: str) -> List[Idea]:
        ideas = []
        shared_context = []
        
        for round_num in range(self.max_rounds):
            round_ideas = []
            for agent in agents:
                # Agent generates ideas based on shared context
                new_ideas = agent.generate_ideas(prompt, shared_context)
                round_ideas.extend(new_ideas)
            
            # Add to shared context
            shared_context.extend(round_ideas)
            ideas.extend(round_ideas)
            
            # Check if enough ideas generated
            if len(ideas) >= self.target_idea_count:
                break
        
        return self.synthesize_ideas(ideas)
```

#### 3. Voting/Consensus Pattern

**Process:**
- Agents vote on proposals
- Aggregate votes
- Select based on consensus criteria

**Implementation:**
```python
class VotingCollaboration:
    def collaborate(self, agents: List[Agent], options: List[Option]) -> Option:
        votes = {}
        for agent in agents:
            votes[agent.id] = agent.vote(options)
        
        # Aggregate votes
        vote_counts = self.aggregate_votes(votes)
        
        # Select based on consensus (e.g., majority, ranked choice)
        return self.select_winner(vote_counts, consensus_method="majority")
```

### Use Cases

**Advantages:**
- ✅ Diverse perspectives
- ✅ Creative problem-solving
- ✅ Robust solutions through debate
- ✅ Democratic decision-making

**Disadvantages:**
- ❌ High communication overhead
- ❌ May not converge
- ❌ Slower than centralized approaches
- ❌ Difficult to coordinate

**Best For:**
- Creative tasks requiring diverse ideas
- Complex problems with no clear solution
- Consensus-building scenarios
- Research and exploration

**Examples:**
- **Design Reviews:** Multiple designers collaborate on design
- **Strategy Planning:** Multiple strategists debate approaches
- **Code Review:** Multiple reviewers discuss implementation
- **Problem Solving:** Multiple experts brainstorm solutions

---

## Hybrid Patterns

### Combining Patterns

Many real-world systems combine multiple patterns:

**Example: Hierarchical + Sequential:**
- Top manager assigns to mid-managers
- Each team uses sequential handoffs
- Results aggregated up hierarchy

**Example: Centralized + Joint Collaboration:**
- Supervisor delegates to worker teams
- Workers collaborate within teams
- Supervisor synthesizes team results

---

## Pattern Selection Guide

| Pattern | Best For | Complexity | Scalability | Flexibility |
|---------|----------|------------|-------------|-------------|
| **Centralized** | Clear hierarchies, controlled workflows | Medium | Medium | Low |
| **Sequential** | Pipeline workflows, linear processes | Low | Low | Low |
| **Hierarchical** | Large systems, multi-level orgs | High | High | Medium |
| **Joint Collaboration** | Creative tasks, consensus building | High | Low | High |

---

**Next:** [4.3 Context Engineering](04-03-context-engineering.md) | [Previous: 4.1 Single Agent Architectures](04-01-single-agent-architectures.md) | [Back to TOC](../../README.md)

