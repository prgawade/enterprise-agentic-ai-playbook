# 5.2 MCP Development

## Overview

The Model Context Protocol (MCP) standardizes how agents access resources and tools. This section covers developing MCP servers, templates, and integrating MCP into enterprise agent systems.

## MCP Templates

### Purpose

Standardize how internal APIs, databases, and resources are exposed to agents through MCP, ensuring consistency, security, and maintainability.

### Template Structure

**Standard MCP Server Template:**
```python
from mcp import MCPServer, Resource, Tool

class EnterpriseMCPServer(MCPServer):
    def __init__(self, config: Config):
        super().__init__(name="enterprise-resources")
        self.config = config
        self.resources = self.register_resources()
        self.tools = self.register_tools()
    
    def register_resources(self) -> List[Resource]:
        """Register available resources"""
        return [
            Resource(
                uri="enterprise://data/customers",
                name="Customer Data",
                description="Access to customer database"
            ),
            Resource(
                uri="enterprise://docs/policies",
                name="Company Policies",
                description="Access to company policy documents"
            )
        ]
    
    def register_tools(self) -> List[Tool]:
        """Register available tools"""
        return [
            Tool(
                name="query_customers",
                description="Query customer database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "filters": {"type": "object"}
                    },
                    "required": ["query"]
                }
            )
        ]
```

### Template Categories

#### 1. Database MCP Templates

**Purpose:** Standardize database access patterns.

**Template:**
```python
class DatabaseMCPTemplate(MCPServer):
    def __init__(self, db_connection: DBConnection, schema: Schema):
        self.db = db_connection
        self.schema = schema
        
        # Register resources based on schema
        for table in schema.tables:
            self.register_resource(
                uri=f"db://{schema.name}/{table.name}",
                name=f"{table.name} Table",
                description=f"Access to {table.name} table"
            )
        
        # Register query tool
        self.register_tool(
            name="query",
            description=f"Query {schema.name} database",
            handler=self.query_handler
        )
    
    def query_handler(self, query: str, filters: Dict) -> Result:
        # Validate query
        validated = self.validate_query(query, filters)
        
        # Execute with security checks
        result = self.db.execute(
            validated,
            user_context=self.get_user_context()
        )
        
        return result
```

#### 2. API Gateway MCP Templates

**Purpose:** Expose internal APIs through MCP.

**Template:**
```python
class APIMCPTemplate(MCPServer):
    def __init__(self, api_config: APIConfig):
        self.api_client = APIClient(api_config)
        
        # Register API endpoints as resources
        for endpoint in api_config.endpoints:
            self.register_resource(
                uri=f"api://{endpoint.path}",
                name=endpoint.name,
                description=endpoint.description
            )
            
            # Create tool for each endpoint
            self.register_tool(
                name=endpoint.name,
                description=endpoint.description,
                inputSchema=endpoint.schema,
                handler=self.create_endpoint_handler(endpoint)
            )
    
    def create_endpoint_handler(self, endpoint: Endpoint):
        def handler(**kwargs):
            # Add authentication
            headers = self.get_auth_headers()
            
            # Call API
            response = self.api_client.call(
                endpoint.path,
                method=endpoint.method,
                params=kwargs,
                headers=headers
            )
            
            return response
        return handler
```

#### 3. File System MCP Templates

**Purpose:** Standardize file system access.

**Template:**
```python
class FileSystemMCPTemplate(MCPServer):
    def __init__(self, base_path: str, permissions: Permissions):
        self.base_path = base_path
        self.permissions = permissions
        
        # Register file system resources
        self.register_tool(
            name="read_file",
            description="Read file contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            },
            handler=self.read_file_handler
        )
    
    def read_file_handler(self, path: str) -> str:
        # Validate path (prevent directory traversal)
        safe_path = self.validate_path(path)
        
        # Check permissions
        if not self.permissions.can_read(safe_path):
            raise PermissionError()
        
        # Read file
        full_path = os.path.join(self.base_path, safe_path)
        with open(full_path, 'r') as f:
            return f.read()
```

---

## MCP Server Implementation

### Core Components

#### 1. Server Registration

**Process:**
- Register server with enterprise MCP registry
- Provide metadata (name, version, capabilities)
- Configure authentication and authorization
- Set up health checks

**Implementation:**
```python
class MCPServerRegistry:
    def register_server(self, server: MCPServer, metadata: ServerMetadata):
        # Validate server
        self.validate_server(server)
        
        # Register in catalog
        self.catalog.register({
            "id": metadata.id,
            "name": metadata.name,
            "version": metadata.version,
            "endpoint": metadata.endpoint,
            "capabilities": server.get_capabilities(),
            "authentication": metadata.auth_config
        })
        
        # Set up health check
        self.setup_health_check(server)
```

#### 2. Resource Discovery

**Process:**
- Agents discover available resources
- Query server for resource list
- Retrieve resource metadata
- Access resources as needed

**Implementation:**
```python
class MCPClient:
    def discover_resources(self, server_id: str) -> List[Resource]:
        server_config = self.registry.get_server(server_id)
        
        # Connect to server
        client = self.connect(server_config)
        
        # List resources
        resources = client.list_resources()
        
        return resources
    
    def get_resource(self, server_id: str, resource_uri: str) -> Resource:
        server_config = self.registry.get_server(server_id)
        client = self.connect(server_config)
        
        return client.get_resource(resource_uri)
```

#### 3. Tool Execution

**Process:**
- Agent selects tool from server
- Validates tool parameters
- Executes tool with security checks
- Returns result to agent

**Implementation:**
```python
class MCPServer:
    def execute_tool(self, tool_name: str, parameters: Dict, context: ExecutionContext) -> Result:
        # Get tool
        tool = self.get_tool(tool_name)
        
        # Validate parameters
        validated = self.validate_parameters(tool, parameters)
        
        # Check authorization
        if not self.authorize(context.user, tool, validated):
            raise AuthorizationError()
        
        # Execute with logging
        with self.log_execution(tool_name, validated, context):
            result = tool.handler(**validated)
        
        # Validate result
        validated_result = self.validate_result(result)
        
        return validated_result
```

### Security Considerations

#### 1. Authentication

**Methods:**
- API keys
- OAuth 2.0
- mTLS
- Service account tokens

**Implementation:**
```python
class MCPServer:
    def authenticate(self, request: Request) -> User:
        # Extract credentials
        credentials = self.extract_credentials(request)
        
        # Validate
        user = self.auth_provider.authenticate(credentials)
        
        if not user:
            raise AuthenticationError()
        
        return user
```

#### 2. Authorization

**Patterns:**
- Role-based access control (RBAC)
- Resource-level permissions
- Tool-level permissions
- Dynamic policy evaluation

**Implementation:**
```python
class MCPServer:
    def authorize(self, user: User, tool: Tool, params: Dict) -> bool:
        # Check user permissions
        if not user.has_permission(f"tools.{tool.name}.execute"):
            return False
        
        # Check resource-level permissions
        resources = tool.get_required_resources(params)
        for resource in resources:
            if not user.can_access(resource):
                return False
        
        # Check dynamic policies
        if not self.policy_engine.evaluate(user, tool, params):
            return False
        
        return True
```

#### 3. Input Validation

**Validation:**
- Schema validation
- Parameter sanitization
- SQL injection prevention
- Path traversal prevention

**Implementation:**
```python
class MCPServer:
    def validate_parameters(self, tool: Tool, params: Dict) -> Dict:
        # Schema validation
        validate(params, tool.inputSchema)
        
        # Sanitize inputs
        sanitized = {}
        for key, value in params.items():
            sanitized[key] = self.sanitize_value(key, value, tool.inputSchema)
        
        return sanitized
```

---

## Building MCP Servers for Common Resources

### Database MCP Server

**Implementation:**
```python
class DatabaseMCPServer(MCPServer):
    def __init__(self, connection_string: str, schema: Schema):
        self.db = Database(connection_string)
        self.schema = schema
        
        # Register tables as resources
        for table in schema.tables:
            self.register_resource(
                uri=f"db://{schema.name}/{table.name}",
                name=table.name,
                description=f"{table.description}"
            )
        
        # Register query tool
        self.register_tool(
            name="query",
            description="Execute SQL query (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "params": {"type": "object"}
                },
                "required": ["sql"]
            },
            handler=self.query_handler
        )
    
    def query_handler(self, sql: str, params: Dict) -> List[Dict]:
        # Validate SQL (prevent injection, ensure read-only)
        validated_sql = self.validate_sql(sql)
        
        # Execute query
        results = self.db.execute(validated_sql, params)
        
        return results
```

### File System MCP Server

**Implementation:**
```python
class FileSystemMCPServer(MCPServer):
    def __init__(self, base_path: str, allowed_patterns: List[str]):
        self.base_path = Path(base_path)
        self.allowed_patterns = [re.compile(p) for p in allowed_patterns]
        
        # Register file operations
        self.register_tool("read_file", self.read_file_handler)
        self.register_tool("list_directory", self.list_directory_handler)
        self.register_tool("write_file", self.write_file_handler)
    
    def read_file_handler(self, path: str) -> str:
        # Validate and resolve path
        safe_path = self.validate_path(path)
        
        # Read file
        full_path = self.base_path / safe_path
        return full_path.read_text()
    
    def validate_path(self, path: str) -> Path:
        # Resolve path (prevent directory traversal)
        resolved = (self.base_path / path).resolve()
        
        # Ensure within base path
        if not str(resolved).startswith(str(self.base_path.resolve())):
            raise ValueError("Path outside allowed directory")
        
        # Check against allowed patterns
        if not any(pattern.match(str(resolved)) for pattern in self.allowed_patterns):
            raise ValueError("Path not allowed")
        
        return resolved.relative_to(self.base_path)
```

---

## Testing MCP Servers

### Unit Testing

**Test Tool Execution:**
```python
def test_mcp_tool_execution():
    server = create_test_server()
    
    result = server.execute_tool(
        "query_customers",
        {"query": "SELECT * FROM customers LIMIT 10"}
    )
    
    assert len(result) <= 10
    assert all("id" in row for row in result)
```

### Integration Testing

**Test Server Registration:**
```python
def test_server_registration():
    registry = MCPRegistry()
    server = create_test_server()
    
    registry.register_server(server, metadata)
    
    discovered = registry.discover_servers()
    assert server.id in [s.id for s in discovered]
```

### Security Testing

**Test Authorization:**
```python
def test_authorization():
    server = create_test_server()
    unauthorized_user = create_user_without_permissions()
    
    with pytest.raises(AuthorizationError):
        server.execute_tool(
            "query_customers",
            {},
            context=ExecutionContext(user=unauthorized_user)
        )
```

---

## Best Practices

### 1. Use Templates

- Start with templates for common patterns
- Customize as needed
- Maintain template library

### 2. Security First

- Implement authentication and authorization
- Validate all inputs
- Log all operations
- Follow least privilege principle

### 3. Documentation

- Document all resources and tools
- Provide usage examples
- Maintain API documentation

### 4. Versioning

- Version MCP servers
- Maintain backward compatibility
- Provide migration guides

### 5. Monitoring

- Monitor server health
- Track usage metrics
- Log all operations
- Set up alerts

---

**Next:** [5.3 Agent Templates](05-03-agent-templates.md) | [Previous: 5.1 Development Frameworks](05-01-development-frameworks.md) | [Back to TOC](../../README.md)

