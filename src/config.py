"""
Configuration module for the distributed task queue.

This module provides configuration settings loaded from environment variables
with sensible defaults. Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by setting the corresponding environment
    variable. Environment variables are case-insensitive.

    Attributes:
        redis_url: Connection URL for Redis server.
            Format: redis://[[username]:[password]@][host][:port][/database]
            Default: redis://localhost:6379

        default_queue: Name of the default queue for task submission.
            Default: "default"

        task_timeout: Maximum time (in seconds) a task can run before timing out.
            Default: 300 seconds (5 minutes)

        max_retries: Maximum number of retry attempts for failed tasks.
            Default: 3

        log_level: Logging level for the application.
            Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
            Default: INFO
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"

    # Queue Configuration
    default_queue: str = "default"
    task_timeout: int = 300  # seconds
    max_retries: int = 3

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @property
    def redis_host(self) -> str:
        """Extract host from Redis URL."""
        # Simple extraction - for more complex URLs, use urllib.parse
        url = self.redis_url.replace("redis://", "")
        if "@" in url:
            url = url.split("@")[1]
        return url.split(":")[0].split("/")[0]

    @property
    def redis_port(self) -> int:
        """Extract port from Redis URL."""
        url = self.redis_url.replace("redis://", "")
        if "@" in url:
            url = url.split("@")[1]
        if ":" in url:
            port_str = url.split(":")[1].split("/")[0]
            return int(port_str)
        return 6379

    @property
    def redis_db(self) -> int:
        """Extract database number from Redis URL."""
        if "/" in self.redis_url.split("://")[1]:
            db_str = self.redis_url.split("/")[-1]
            if db_str.isdigit():
                return int(db_str)
        return 0


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    This function returns a cached Settings instance to avoid
    repeatedly reading environment variables and .env file.

    Returns:
        Settings: The application settings instance.

    Example:
        >>> settings = get_settings()
        >>> print(settings.redis_url)
        redis://localhost:6379
    """
    return Settings()
