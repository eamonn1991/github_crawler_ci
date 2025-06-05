# GitHub Repository Crawler

A high-performance, multi-threaded GitHub repository crawler that uses GraphQL API to fetch repository data efficiently. The crawler supports various search criteria and can handle rate limiting automatically.

## Features

- Multi-threaded crawling with automatic token rotation
- Smart date-based partitioning for comprehensive coverage
- Efficient database operations with selective updates
- Automatic rate limit handling and backoff
- Detailed performance metrics and statistics

## Prerequisites

- Python 3.7+
- PostgreSQL database
- GitHub API tokens (personal access tokens)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/eamonn1991/test-1.git
cd github_graphql_learn
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your database:
```bash
# Create database and run migrations
python src/models.py
```

## Configuration

1. Create a `config.py` file in the root directory with your settings:
```python
class Settings:
    # Database
    database_url = "postgresql://user:password@localhost:5432/github_crawler"
    
    # GitHub API
    github_api_url = "https://api.github.com/graphql"
    github_token_multi_thread = [
        "your-token-1",
        "your-token-2",
        # Add more tokens for better performance
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
```

2. Set up your GitHub tokens:
   - Generate personal access tokens from GitHub (Settings -> Developer settings -> Personal access tokens)
   - Add tokens to `config.py`
   - Required permissions: `repo`, `read:user`

## Usage

### Basic Usage

Run the crawler with default settings:
```bash
python src/crawler.py
```

### Advanced Usage

The crawler supports various command-line arguments:

```bash
python src/crawler.py \
  --mode pipeline \
  --min-stars 1000 \
  --language python \
  --batch-size 50 \
  --keywords "machine learning" \
  --sort-by stars \
  --start-year 2023 \
  --start-month 1 \
  --partition-threshold 500 \
  --total-num-repo 5000
```

Available arguments:
- `--mode`: Choose between 'pipeline' (full crawl) or 'single' (one fetch)
- `--min-stars`: Minimum star count for repositories
- `--language`: Programming language filter
- `--batch-size`: Number of repositories per request (max 100)
- `--keywords`: Search keywords
- `--sort-by`: Sort results by 'stars', 'updated', 'created', or 'forks'
- `--start-year`: Starting year for crawling
- `--start-month`: Starting month for crawling
- `--partition-threshold`: Repos per date range before moving on
- `--total-num-repo`: Total number of repositories to fetch

### Single Mode

Test the crawler with a single API call:
```bash
python src/crawler.py --mode single --min-stars 1000 --language python
```

## Architecture

The crawler uses a clean architecture approach with several key components:

1. **Token Manager**: Handles token rotation and rate limiting
2. **Anti-Corruption Layer**: Isolates GitHub API specifics from core logic
3. **Thread-Safe Components**: Ensures safe concurrent operations
4. **Database Layer**: Efficient batch operations with selective updates

## Performance

The crawler is optimized for performance:
- Multi-threading with token rotation
- Batch database operations
- Selective updates (only when star count changes)
- Smart date-based partitioning
- Automatic rate limit management

Performance metrics are displayed during crawling:
- Average crawl and write times
- Total repositories fetched
- Per-thread statistics
- Effective parallel speedup

## Error Handling

The crawler handles various error conditions:
- Rate limit exceeded
- API errors
- Network issues
- Database connection problems

Automatic retry mechanism with configurable retry count.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE) 