from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional

def reload_env():
    """Reload environment variables from .env file"""
    load_dotenv(override=True)

class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    Environment variables will be automatically loaded and type-converted.
    """
    # GitHub Configuration
    github_token: Optional[str] = Field(None, description="Single GitHub API token for authentication")
    github_token_multi_thread: Optional[str] = Field(None, description="Comma-separated GitHub API tokens for multi-threading")
    github_api_url: str = Field(
        default="https://api.github.com/graphql",
        description="GitHub GraphQL API endpoint"
    )

    # Database Configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="star_crawler_edison", description="Database name")
    db_user: str = Field(default="edison", description="Database user")
    db_password: str = Field(default="postgres", description="Database password")

    # Crawler Configuration
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of repositories to fetch per request (max 100)"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retry attempts for failed requests"
    )
    total_num_repo: int = Field(
        default=100000,
        ge=1,
        description="Total number of repositories to fetch"
    )
    default_min_stars: int = Field(
        default=10,
        ge=0,
        description="Default minimum number of stars for repository filtering"
    )

    # Default Crawl Settings
    default_start_year: int = Field(
        default=2025,
        ge=2008,
        le=2025,
        description="Default starting year for repository search"
    )
    default_start_month: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Default starting month for repository search"
    )
    default_partition_threshold: int = Field(
        default=900,
        gt=0,
        le=1000,
        description="Number of repos to fetch before changing date range (max 1000)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    """Get cached settings"""
    return Settings()

def get_fresh_settings():
    """Get fresh settings, bypassing the cache"""
    get_settings.cache_clear()
    reload_env()
    return get_settings()

# Initialize settings with fresh values
settings = get_fresh_settings()