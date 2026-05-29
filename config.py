"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Bedrock (using long-term API key)
    bedrock_api_key: str = Field(..., description="Bedrock long-term API key")
    aws_region: str = Field(default="us-east-1", description="AWS region")

    # LlamaParse
    llama_cloud_api_key: str = Field(..., description="LlamaParse API key")

    # Database
    database_url: str = Field(
        default="postgresql://ai_tutor:dev_password@localhost:5432/ai_tutor_dev",
        description="PostgreSQL connection string"
    )

    # Models
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock embedding model ID"
    )
    bedrock_llm_model_primary: str = Field(
        default="moonshotai.kimi-k2.5",
        description="Primary LLM model for analysis"
    )
    bedrock_llm_model_secondary: str = Field(
        default="minimax.minimax-m2.5",
        description="Secondary LLM model for analysis"
    )

    # Rate limiting
    max_concurrent_parses: int = Field(default=3, description="Max concurrent PDF parses")
    parse_batch_size: int = Field(default=5, description="Number of docs to parse before checkpoint")
    retry_max_attempts: int = Field(default=5, description="Max retry attempts per document")
    retry_base_delay: float = Field(default=2.0, description="Base delay for exponential backoff (seconds)")
    retry_max_delay: float = Field(default=300.0, description="Max delay for exponential backoff (seconds)")

    # Embedding settings
    embedding_batch_size: int = Field(default=25, description="Chunks per embedding batch")
    max_concurrent_embeddings: int = Field(default=10, description="Max concurrent embedding requests")

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable auto-reload for development")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    # Context Window
    context_window_size: int = Field(default=32000, description="LLM context window size (tokens)")
    context_warning_threshold: float = Field(default=0.8, description="Trigger summarization at this threshold (0-1)")

    # Scheduler
    export_hour: int = Field(default=4, description="Hour for daily conversation export (0-23)")
    export_timezone: str = Field(default="Europe/Berlin", description="Timezone for scheduled tasks")

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="CHANGE_THIS_IN_PRODUCTION_USE_SECRETS_MANAGER_256BIT_RANDOM_KEY",
        description="JWT secret key (256-bit random)"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=60, description="Access token expiry (minutes)")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry (days)")

    # Professor Registration
    professor_registration_code: str = Field(
        default="!yAHeq2v@L59MV",
        description="Access code for professor registration"
    )

    # File Upload
    file_storage_type: str = Field(default="local", description="Storage type: 'local' or 's3'")
    file_storage_path: str = Field(default="./uploads", description="Local storage path")
    aws_s3_bucket: str = Field(default="ai-tutor-uploads", description="S3 bucket name")
    max_file_size_mb: int = Field(default=100, description="Max file size (MB)")

    # Email/SMTP Settings
    smtp_host: str = Field(default="localhost", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username (optional)")
    smtp_password: str = Field(default="", description="SMTP password (optional)")
    from_email: str = Field(default="noreply@ai-tutor.local", description="From email address")

    # AWS Credentials (for Bedrock)
    aws_access_key_id: str = Field(default="", description="AWS Access Key ID")
    aws_secret_access_key: str = Field(default="", description="AWS Secret Access Key")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
