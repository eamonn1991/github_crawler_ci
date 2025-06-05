class Settings:
    # Database
    database_url = "postgresql://user:password@localhost:5432/github_crawler"
    
    # GitHub API
    github_api_url = "https://api.github.com/graphql"
    github_token_multi_thread = [
        "your-token-1",
        "your-token-2",
    ]
    
    # Crawler Settings
    batch_size = 50  # Max 100
    total_num_repo = 10000
    max_retries = 3
    default_min_stars = 100
    default_partition_threshold = 1000
    default_start_year = 2024
    default_start_month = 1

settings = Settings() 