from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
import os

class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    Environment variables will be automatically loaded and type-converted.
    """
    model_config = ConfigDict(extra='ignore')

    # GitHub Configuration
    github_token: str = Field(
        default=os.environ.get('GITHUB_TOKEN', ''),
        description="GitHub API token for authentication"
    )
    github_api_url: str = Field(
        default="https://api.github.com/graphql",
        description="GitHub GraphQL API endpoint"
    )

    # Database Configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(
        default="github_crawler_test",
        description="Database name"
    )
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(
        default="postgres",
        description="Database password"
    )

    # Test-specific settings
    batch_size: int = Field(default=5, ge=1, le=100)
    max_retries: int = Field(default=3, ge=1)
    total_num_repo: int = Field(default=100, ge=1)
    default_min_stars: int = Field(default=100, ge=0)
    default_start_year: int = Field(default=2024, ge=2008, le=2025)
    default_start_month: int = Field(default=1, ge=1, le=12)
    default_partition_threshold: int = Field(
        default=100,
        gt=0,
        le=1000
    )

    @property
    def database_url(self) -> str:
        """Generate the database URL from components"""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

# Initialize settings
settings = Settings()