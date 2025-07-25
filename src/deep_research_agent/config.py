"""
Deep Research Agent Configuration

Comprehensive configuration system supporting environment variables,
file-based config, and runtime customization.
"""

import os
import json
from typing import Optional, Any
from pathlib import Path
from dataclasses import dataclass, field

from .models import SearchAPI, MCPServerConfig

# ============================================================================
# Main Configuration Class
# ============================================================================

@dataclass
class DeepResearchConfig:
    """
    Main configuration class for Deep Research Agent.
    
    Supports loading from environment variables, JSON files,
    and programmatic configuration.
    """
    
    # General Settings
    max_concurrent_research_units: int = 5
    max_researcher_iterations: int = 3
    max_react_tool_calls: int = 5
    allow_clarification: bool = True

    # Search Configuration
    search_api: SearchAPI = SearchAPI.TAVILY_MCP
    max_search_results: int = 5

    # Model Configuration (OpenAI models only)
    clarification_model_name: str = "gpt-4.1-mini"
    research_brief_model_name: str = "gpt-4.1-mini"
    supervisor_model_name: str = "gpt-4.1-mini"
    researcher_model_name: str = "gpt-4.1-mini"
    compression_model_name: str = "gpt-4.1-nano"
    final_report_model_name: str = "gpt-4.1"

    # API Keys
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    
    # Environment settings
    environment: str = "development"  # development, staging, production
    debug_mode: bool = False
    enable_tracing: bool = True
    
    # Session and storage
    enable_sessions: bool = True
    session_db_path: str = "./deep_research_sessions.db"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Internal list for MCP servers if enabled dynamically
    _mcp_servers_internal: list[MCPServerConfig] = field(default_factory=list, init=False, repr=False)


    @classmethod
    def from_environment(cls) -> "DeepResearchConfig":
        """
        Create configuration from environment variables.
        """
        return cls(
            max_concurrent_research_units=int(os.getenv("DEEP_RESEARCH_MAX_CONCURRENT_UNITS", "5")),
            max_researcher_iterations=int(os.getenv("DEEP_RESEARCH_MAX_ITERATIONS", "3")),
            max_react_tool_calls=int(os.getenv("DEEP_RESEARCH_MAX_TOOL_CALLS", "5")),
            allow_clarification=_str_to_bool(os.getenv("DEEP_RESEARCH_ALLOW_CLARIFICATION", "true")),
            search_api=SearchAPI(os.getenv("DEEP_RESEARCH_SEARCH_API", "tavily_mcp")),
            max_search_results=int(os.getenv("DEEP_RESEARCH_MAX_SEARCH_RESULTS", "5")),

            clarification_model_name=os.getenv("DEEP_RESEARCH_CLARIFICATION_MODEL", "gpt-4.1-mini"),
            research_brief_model_name=os.getenv("DEEP_RESEARCH_BRIEF_MODEL", "gpt-4.1-mini"),
            supervisor_model_name=os.getenv("DEEP_RESEARCH_SUPERVISOR_MODEL", "gpt-4.1-mini"),
            researcher_model_name=os.getenv("DEEP_RESEARCH_RESEARCHER_MODEL", "gpt-4.1-mini"),
            compression_model_name=os.getenv("DEEP_RESEARCH_COMPRESSION_MODEL", "gpt-4.1-mini"),
            final_report_model_name=os.getenv("DEEP_RESEARCH_FINAL_REPORT_MODEL", "gpt-4.1"),

            openai_api_key=os.getenv("OPENAI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug_mode=_str_to_bool(os.getenv("DEBUG_MODE", "false")),
            enable_tracing=_str_to_bool(os.getenv("ENABLE_TRACING", "true")),
            enable_sessions=_str_to_bool(os.getenv("ENABLE_SESSIONS", "true")),
            session_db_path=os.getenv("SESSION_DB_PATH", "./deep_research_sessions.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    
    
    @classmethod
    def for_environment(cls, env: str) -> "DeepResearchConfig":
        """
        Create configuration optimized for specific environment.
        """
        base_config = cls.from_environment()
        base_config.environment = env
        
        if env == "development":
            base_config.max_concurrent_research_units = 2
            base_config.max_researcher_iterations = 2
            base_config.max_react_tool_calls = 3
            base_config.debug_mode = True
            base_config.log_level = "DEBUG"
            
        elif env == "staging":
            base_config.max_concurrent_research_units = 3
            base_config.max_researcher_iterations = 3
            base_config.max_react_tool_calls = 4
            base_config.debug_mode = False
            base_config.log_level = "INFO"
            
        elif env == "production":
            base_config.max_concurrent_research_units = 5
            base_config.max_researcher_iterations = 3
            base_config.max_react_tool_calls = 5
            base_config.debug_mode = False
            base_config.log_level = "WARNING"
            base_config.enable_tracing = True
            
        return base_config
    
    def get_tavily_mcp_config(self) -> MCPServerConfig:
        """
        Create Tavily MCP server configuration using SSE transport.
        """
        if not self.tavily_api_key:
            raise ValueError("Tavily API key is required for MCP server configuration")
        
        return MCPServerConfig(
            name="tavily-search",
            url=f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.tavily_api_key}",
            timeout=30.0,
            sse_read_timeout=300.0,
            cache_tools_list=True,
            convert_schemas_to_strict=True
        )
    
    def enable_tavily_mcp(self) -> None:
        """
        Enable Tavily MCP server with SSE transport.
        """
        self.search_api = SearchAPI.TAVILY_MCP
        
        tavily_config = self.get_tavily_mcp_config()
        
        # Ensure only one Tavily config
        self._mcp_servers_internal = [
            server for server in self._mcp_servers_internal
            if server.name != "tavily-search"
        ]
        self._mcp_servers_internal.append(tavily_config)

    def get_mcp_servers(self) -> list[MCPServerConfig]:
        """Returns the list of enabled MCP servers."""
        return self._mcp_servers_internal
    
    def validate(self) -> list[str]:
        """
        Validate configuration and return list of issues.
        """
        errors = []
        
        # Check API keys
        if not self.openai_api_key:
            errors.append("OpenAI API key is required")
        
        if self.search_api == SearchAPI.TAVILY_MCP and not self.tavily_api_key:
            errors.append("Tavily API key is required when using Tavily MCP search")
        
        # Validate model names
        model_names = [
            self.clarification_model_name,
            self.research_brief_model_name,
            self.supervisor_model_name,
            self.researcher_model_name,
            self.compression_model_name,
            self.final_report_model_name,
        ]
        
        for model_name in model_names:
            if not model_name:
                errors.append(f"Model name cannot be empty for one of the agents.")

        # Validate numeric constraints
        if self.max_concurrent_research_units < 1:
            errors.append("max_concurrent_research_units must be at least 1")
        
        if self.max_researcher_iterations < 1:
            errors.append("max_researcher_iterations must be at least 1")
        
        if self.max_react_tool_calls < 1:
            errors.append("max_react_tool_calls must be at least 1")
        
        # Validate MCP server configurations (only if they exist)
        for i, mcp_config in enumerate(self._mcp_servers_internal):
            if not mcp_config.url:
                errors.append(f"MCP server {i}: URL is required.")
        
        return errors
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.
        """
        # Convert enum to its value for serialization
        search_api_value = self.search_api.value if isinstance(self.search_api, SearchAPI) else self.search_api

        return {
            "max_concurrent_research_units": self.max_concurrent_research_units,
            "max_researcher_iterations": self.max_researcher_iterations,
            "max_react_tool_calls": self.max_react_tool_calls,
            "allow_clarification": self.allow_clarification,
            "search_api": search_api_value,
            "max_search_results": self.max_search_results,
            "clarification_model_name": self.clarification_model_name,
            "research_brief_model_name": self.research_brief_model_name,
            "supervisor_model_name": self.supervisor_model_name,
            "researcher_model_name": self.researcher_model_name,
            "compression_model_name": self.compression_model_name,
            "final_report_model_name": self.final_report_model_name,
            "openai_api_key": "***" if self.openai_api_key else None,
            "tavily_api_key": "***" if self.tavily_api_key else None,
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "enable_tracing": self.enable_tracing,
            "enable_sessions": self.enable_sessions,
            "session_db_path": self.session_db_path,
            "log_level": self.log_level,
            # _mcp_servers_internal is not serialized directly as it's populated dynamically
        }
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to JSON file.
        """
        config_data = self.to_dict()
        # API keys are already masked/omitted by to_dict
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True);
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)


# ============================================================================
# Helper Functions
# ============================================================================

def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("true", "1", "yes", "on")


# ============================================================================
# Default Configurations
# ============================================================================

def get_default_config() -> DeepResearchConfig:
    """Get default configuration for development."""
    return DeepResearchConfig.for_environment("development")


def get_production_config() -> DeepResearchConfig:
    """Get production-optimized configuration."""
    return DeepResearchConfig.for_environment("production") 