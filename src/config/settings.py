from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    
    # Server Configuration
    mcp_host: str = Field(default="0.0.0.0", env="MCP_HOST")
    mcp_port: int = Field(default=8000, env="MCP_PORT")
    mcp_env: str = Field(default="development", env="MCP_ENV")
    mcp_log_level: str = Field(default="INFO", env="MCP_LOG_LEVEL")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    
    # Vector Store Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="agenticrag", env="CHROMA_COLLECTION_NAME")
    chroma_host: Optional[str] = Field(default=None, env="CHROMA_HOST")
    chroma_port: Optional[int] = Field(default=None, env="CHROMA_PORT")
    
    # Model Configuration
    embedding_model: str = Field(default="text-embedding-3-large", env="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=100, env="EMBEDDING_BATCH_SIZE")
    retrieval_model: str = Field(default="gpt-4.1", env="RETRIEVAL_MODEL")
    compression_model: str = Field(default="gpt-4.1-mini", env="COMPRESSION_MODEL")
    max_tokens_retrieval: int = Field(default=10000, env="MAX_TOKENS_RETRIEVAL")
    max_tokens_compression: int = Field(default=5000, env="MAX_TOKENS_COMPRESSION")
    
    # Chunking Configuration
    chunk_size_tokens: int = Field(default=1280, env="CHUNK_SIZE_TOKENS")
    chunk_overlap_tokens: int = Field(default=50, env="CHUNK_OVERLAP_TOKENS")
    max_file_size_mb: float = Field(default=2.0, env="MAX_FILE_SIZE_MB")
    
    # Cost Control
    daily_budget_usd: float = Field(default=100.0, env="DAILY_BUDGET_USD")
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    
    # Security
    api_key: str = Field(default="your-secret-api-key", env="API_KEY")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "https://localhost:3000"]
    )
    
    @validator("allowed_origins", pre=True, always=True)
    def parse_allowed_origins(cls, v, values):
        # Get from environment if not provided
        if v is None:
            import os
            env_value = os.environ.get("ALLOWED_ORIGINS")
            if env_value:
                v = env_value
        
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or ["http://localhost:3000", "https://localhost:3000"]
    
    @property
    def is_development(self) -> bool:
        return self.mcp_env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.mcp_env == "production"
    
    @property
    def chroma_settings(self) -> dict:
        if self.chroma_host and self.chroma_port:
            return {
                "chroma_client_auth_provider": "chromadb.auth.token.TokenAuthClientProvider",
                "chroma_client_auth_credentials": self.api_key,
                "chroma_server_host": self.chroma_host,
                "chroma_server_http_port": self.chroma_port,
            }
        return {
            "persist_directory": self.chroma_persist_directory,
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()