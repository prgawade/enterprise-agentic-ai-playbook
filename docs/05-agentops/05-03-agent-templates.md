# 5.3 Agent Templates

## Overview

Agent templates provide reusable blueprints for common agent patterns, enabling rapid development, consistency, and best practices. This section explores template design, implementation, and management.

## What are Agent Templates?

**Definition:** Pre-configured agent configurations that encapsulate role, capabilities, tools, and behavioral patterns for specific use cases.

**Benefits:**
- **Rapid Development:** Start with proven patterns
- **Consistency:** Standardized behavior across agents
- **Best Practices:** Incorporate lessons learned
- **Maintainability:** Centralized updates benefit all instances

---

## Template Categories

### 1. Domain-Specific Templates

#### The Data Analyst Agent

**Purpose:** Analyze data, generate insights, create reports.

**Components:**
- **Role:** Senior Data Analyst
- **Capabilities:** SQL queries, statistical analysis, visualization
- **Tools:** Database connector, visualization library, reporting tools
- **Memory:** Query history, user preferences, report templates
- **Personality:** Analytical, detail-oriented, thorough

**Template Configuration:**
```yaml
name: data-analyst-agent
role: Senior Data Analyst
system_prompt: |
  You are a senior data analyst with expertise in SQL, statistical analysis,
  and data visualization. Your goal is to help users understand their data
  through analysis, insights, and clear visualizations.
  
  Always:
  - Verify data quality before analysis
  - Provide context and explanations with results
  - Suggest follow-up analyses when appropriate
  - Use clear, non-technical language when presenting results

tools:
  - database_query
  - data_visualization
  - statistical_analysis
  - report_generation

memory:
  type: vector
  stores:
    - query_history
    - user_preferences
    - analysis_patterns

constraints:
  - max_query_complexity: medium
  - require_approval_for: [data_exports, schema_changes]
  - data_access_scope: [sales, customer, product]
```

#### The HR Concierge Agent

**Purpose:** Assist with HR-related questions and tasks.

**Components:**
- **Role:** HR Assistant
- **Capabilities:** Policy lookup, leave requests, benefits information
- **Tools:** HRIS integration, policy database, calendar
- **Memory:** Employee information, policy history, preferences
- **Personality:** Friendly, helpful, empathetic

**Template Configuration:**
```yaml
name: hr-concierge-agent
role: HR Assistant
system_prompt: |
  You are a friendly HR assistant helping employees with HR-related questions
  and tasks. Be empathetic, clear, and always prioritize employee privacy.
  
  Capabilities:
  - Answer policy questions
  - Help with leave requests
  - Provide benefits information
  - Schedule HR meetings

tools:
  - hris_query
  - policy_search
  - leave_request
  - calendar_booking

memory:
  type: hybrid
  stores:
    - employee_preferences
    - interaction_history
    - policy_access_log

constraints:
  - privacy_mode: strict
  - require_approval_for: [personal_data_access, leave_approvals]
  - data_access_scope: [own_data, public_policies]
```

#### The Customer Support Agent

**Purpose:** Handle customer inquiries and support requests.

**Components:**
- **Role:** Customer Support Specialist
- **Capabilities:** Ticket management, knowledge base search, order lookup
- **Tools:** CRM, knowledge base, order system, communication channels
- **Memory:** Customer history, solution patterns, escalation rules
- **Personality:** Professional, empathetic, solution-oriented

**Template Configuration:**
```yaml
name: customer-support-agent
role: Customer Support Specialist
system_prompt: |
  You are a customer support specialist dedicated to helping customers
  resolve their issues quickly and satisfactorily.
  
  Guidelines:
  - Always be empathetic and professional
  - Search knowledge base before responding
  - Escalate complex issues appropriately
  - Follow up on unresolved tickets

tools:
  - crm_query
  - knowledge_base_search
  - ticket_management
  - order_lookup
  - email_send

memory:
  type: graph
  stores:
    - customer_interaction_history
    - solution_patterns
    - escalation_history

constraints:
  - max_resolution_time: 24_hours
  - require_human_escalation_for: [refunds, account_changes]
  - communication_style: professional_friendly
```

---

### 2. Functional Templates

#### The Researcher Agent

**Purpose:** Conduct research, gather information, synthesize findings.

**Template:**
```yaml
name: researcher-agent
role: Research Assistant
capabilities:
  - web_search
  - document_analysis
  - information_synthesis
  - citation_management

tools:
  - web_search
  - document_reader
  - citation_tool
  - note_taking

workflow:
  - search_and_gather
  - analyze_sources
  - synthesize_findings
  - cite_sources
```

#### The Writer Agent

**Purpose:** Create written content based on requirements.

**Template:**
```yaml
name: writer-agent
role: Content Writer
capabilities:
  - content_creation
  - style_adaptation
  - editing
  - formatting

tools:
  - document_writer
  - style_checker
  - grammar_checker
  - template_loader

workflow:
  - understand_requirements
  - create_outline
  - write_content
  - review_and_edit
```

#### The Reviewer Agent

**Purpose:** Review and validate content, code, or decisions.

**Template:**
```yaml
name: reviewer-agent
role: Quality Reviewer
capabilities:
  - content_review
  - quality_assessment
  - feedback_generation
  - approval_workflow

tools:
  - review_checklist
  - quality_metrics
  - feedback_template
  - approval_system

workflow:
  - receive_submission
  - review_against_criteria
  - generate_feedback
  - approve_or_request_changes
```

---

## Template Implementation

### Template Structure

**Standard Template Format:**
```python
@dataclass
class AgentTemplate:
    name: str
    role: str
    system_prompt: str
    tools: List[ToolConfig]
    memory_config: MemoryConfig
    constraints: AgentConstraints
    workflow: Optional[WorkflowConfig]
    personality: Optional[PersonalityConfig]
```

### Template Instantiation

**Process:**
```python
class AgentTemplateEngine:
    def create_agent(self, template_name: str, customization: Dict) -> Agent:
        # Load template
        template = self.load_template(template_name)
        
        # Apply customizations
        config = self.apply_customizations(template, customization)
        
        # Instantiate agent
        agent = Agent(
            role=config.role,
            system_prompt=config.system_prompt,
            tools=self.initialize_tools(config.tools),
            memory=self.initialize_memory(config.memory_config),
            constraints=config.constraints
        )
        
        return agent
```

### Template Customization

**Customization Points:**
- Tool configuration
- Memory settings
- Constraint adjustments
- Personality traits
- Workflow modifications

**Example:**
```python
# Create agent from template with customization
agent = template_engine.create_agent(
    template_name="data-analyst-agent",
    customization={
        "tools": {
            "database_query": {
                "connection": "production_db",
                "query_timeout": 30
            }
        },
        "constraints": {
            "data_access_scope": ["sales", "marketing"]  # Restricted scope
        },
        "personality": {
            "communication_style": "technical"  # Override default
        }
    }
)
```

---

## Template Library Management

### Template Registry

**Structure:**
```
templates/
  ├── domain/
  │   ├── data-analyst.yaml
  │   ├── hr-concierge.yaml
  │   └── customer-support.yaml
  ├── functional/
  │   ├── researcher.yaml
  │   ├── writer.yaml
  │   └── reviewer.yaml
  └── custom/
      └── organization-specific/
```

### Template Versioning

**Versioning Strategy:**
- Semantic versioning (major.minor.patch)
- Backward compatibility considerations
- Migration guides for major versions

**Implementation:**
```yaml
template:
  name: data-analyst-agent
  version: 2.1.0
  description: Data analyst agent template
  changelog:
    - version: 2.1.0
      changes: Added new visualization tools
    - version: 2.0.0
      changes: Major rewrite with new memory system
  compatibility:
    min_agent_framework_version: 1.5.0
```

### Template Validation

**Validation Checks:**
- Schema validation
- Tool availability
- Memory configuration validity
- Constraint consistency
- Workflow correctness

**Implementation:**
```python
class TemplateValidator:
    def validate(self, template: AgentTemplate) -> ValidationResult:
        errors = []
        
        # Schema validation
        errors.extend(self.validate_schema(template))
        
        # Tool validation
        errors.extend(self.validate_tools(template.tools))
        
        # Memory validation
        errors.extend(self.validate_memory(template.memory_config))
        
        # Constraint validation
        errors.extend(self.validate_constraints(template.constraints))
        
        return ValidationResult(errors=errors, valid=len(errors) == 0)
```

---

## Best Practices

### 1. Template Design

**Principles:**
- **Single Responsibility:** Each template should have a clear, focused purpose
- **Flexibility:** Allow customization for specific use cases
- **Composability:** Templates should work well together
- **Documentation:** Clear documentation of purpose and usage

### 2. Template Maintenance

**Practices:**
- Regular review and updates
- Version control for templates
- Backward compatibility when possible
- Clear deprecation process

### 3. Template Sharing

**Strategies:**
- Centralized template repository
- Template marketplace (internal or external)
- Community contributions
- Template ratings and reviews

### 4. Testing Templates

**Approaches:**
- Unit tests for template validation
- Integration tests for template instantiation
- Acceptance tests for template behavior
- Performance tests for template efficiency

---

## Example: Building a Custom Template

### Step 1: Define Requirements

- Purpose and use case
- Required capabilities
- Tools needed
- Memory requirements
- Constraints and guardrails

### Step 2: Create Template Configuration

```yaml
name: project-manager-agent
role: Project Manager Assistant
system_prompt: |
  You are a project manager assistant helping with project planning,
  tracking, and coordination.
  
  Responsibilities:
  - Track project status and milestones
  - Coordinate team communication
  - Generate status reports
  - Identify risks and blockers

tools:
  - project_management_system
  - task_tracker
  - team_communication
  - report_generator

memory:
  type: hybrid
  stores:
    - project_history
    - team_preferences
    - status_patterns

constraints:
  - read_only_for: [financial_data]
  - require_approval_for: [milestone_changes, resource_allocation]
```

### Step 3: Validate and Test

- Validate template schema
- Test template instantiation
- Verify tool integration
- Test workflow execution

### Step 4: Document and Publish

- Write usage documentation
- Provide examples
- Add to template registry
- Share with team

---

**Next:** [5.4 Feedback & Learning](05-04-feedback-learning.md) | [Previous: 5.2 MCP Development](05-02-mcp-development.md) | [Back to TOC](../../README.md)

