from dataclasses import dataclass, field
from typing import List, Optional, Any
import os

@dataclass
class ModelConfig:
    model_type: str  # ollama, gemini, claude

    @staticmethod
    def validate_model_type(model_type: str) -> bool:
        return model_type in ['ollama', 'gemini', 'claude']

@dataclass
class MCPServerConfig:
    host: str
    port: int
    api_key: Optional[str] = field(default=None)

    def validate(self) -> bool:
        return isinstance(self.host, str) and isinstance(self.port, int)

@dataclass
class ReportConfig:
    output_format: str  # e.g., 'pdf', 'csv'
    include_timestamp: bool = True

    def generate_report(self, data: List[Any]) -> str:
        # Placeholder for report generation logic
        return f'Report generated in {self.output_format} format.'

@dataclass
class AgentConfig:
    environment_variable: str

    def get_env_variable(self) -> str:
        return os.getenv(self.environment_variable, 'Variable not set')

    @staticmethod
    def validate_environment_variable(var: str) -> bool:
        return var in os.environ
