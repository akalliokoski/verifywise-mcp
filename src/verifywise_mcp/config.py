"""Configuration module for the VerifyWise MCP server.

Reads all settings from environment variables with the ``VERIFYWISE_`` prefix.
An optional ``.env`` file is also supported for local development.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """VerifyWise MCP server configuration.

    All fields are read from environment variables prefixed with ``VERIFYWISE_``.
    Example: ``VERIFYWISE_EMAIL=admin@example.com``.
    """

    model_config = SettingsConfigDict(
        env_prefix="VERIFYWISE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(
        default="http://localhost:3000",
        description="VerifyWise API base URL",
    )
    email: str = Field(
        description="VerifyWise admin email address",
    )
    password: str = Field(
        description="VerifyWise admin password",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR",
    )
    transport: str = Field(
        default="stdio",
        description="MCP transport mode: stdio or http",
    )
    http_port: int = Field(
        default=8080,
        description="HTTP transport port (only used when transport=http)",
    )
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed API requests",
    )
