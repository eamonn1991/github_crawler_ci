import requests
import time
from datetime import datetime
import pytz
import argparse
import calendar
import logging
from typing import Dict, Any, List
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from src.models import Repository, get_db
from src.config import settings

# Disable logging from other libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# Configure root logger to only show messages without timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Only show the message without timestamp or level
    force=True  # Override any existing configuration
)

class TokenManager:
    def __init__(self, token):
        """Initialize with a single token or a list of tokens"""
        self.tokens = [token] if isinstance(token, str) else token
        self.current_index = 0
        self.lock = Lock()
        
    def get_token(self):
        """Get the next token in a thread-safe manner"""
        with self.lock:
            token = self.tokens[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.tokens)
            return token

class ThreadSafeCounter:
    def __init__(self, initial=0):
        self.value = initial
        self.lock = Lock()
        
    def increment(self, amount=1):
        with self.lock:
            self.value += amount
            return self.value
            
    def get(self):
        with self.lock:
            return self.value
            
    def set(self, value):
        with self.lock:
            self.value = value

# Constants from Config
GITHUB_API_URL = settings.github_api_url
BATCH_SIZE = settings.batch_size

# Initialize token manager with the GitHub token
token_manager = TokenManager(settings.github_token)

def check_total_repos(shared_counters, target_total):
    """Helper function to check if we've reached the target total"""
    return shared_counters['total'].get() >= target_total

def send_crawl_request(query, variables=None):
    """
    Creates a GraphQL request with proper headers and authentication
    """
    token = token_manager.get_token()
    print(f"Using API URL: {GITHUB_API_URL}")
    print(f"Token (first 10 chars): {token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    json_data = {
        'query': query,
        'variables': variables or {}
    }
    
    print("Request headers:", {k: '***' if k == 'Authorization' else v for k, v in headers.items()})
    print("Request data:", json_data)
    
    return requests.post(GITHUB_API_URL, json=json_data, headers=headers)

def build_search_query(
    min_stars=0,
    language=None,
    created_after=None,  # Format: YYYY-MM-DD
    created_before=None, # Format: YYYY-MM-DD
    keywords=None,      # Keywords to search in code/description
    sort_by=None
):
    """
    Builds a GitHub search query with various filters
    
    Parameters:
    - min_stars: Minimum number of stars
    - language: Programming language (e.g., "python", "javascript")
    - created_after: Created after date (YYYY-MM-DD)
    - created_before: Created before date (YYYY-MM-DD)
    - keywords: List of keywords to search in code/description
    - sort_by: How to sort results ("stars", "updated", "created", "forks")
    """
    # Start with base query
    query_parts = []
    
    # Add keywords if provided
    if keywords:
        query_parts.extend(keywords)
    
    # Add language filter
    if language:
        query_parts.append(f"language:{language}")
    
    # Add stars filter
    if min_stars:
        query_parts.append(f"stars:>={min_stars}")
    
    # Add creation date filter
    if created_after and created_before:
        query_parts.append(f"created:{created_after}..{created_before}")
    elif created_after:
        query_parts.append(f"created:>{created_after}")
    elif created_before:
        query_parts.append(f"created:<{created_before}")
    
    # Add sort
    sort_mapping = {
        "stars": "stars",
        "updated": "updated",
        "created": "created",
        "forks": "forks"
    }
    if sort_by and sort_by.lower() != 'none':
        sort_term = sort_mapping.get(sort_by, "stars")
        query_parts.append(f"sort:{sort_term}")
    
    return " ".join(query_parts)

def fetch_repositories(
    batch_size=5,
    min_stars=1,
    language=None,
    created_after=None,
    created_before=None,
    keywords=None,
    sort_by=None,
    after_cursor=None  # For pagination
):
    """
    Fetches repositories using GitHub's GraphQL API with enhanced search options
    """
    search_query = build_search_query(
        min_stars=min_stars,
        language=language,
        created_after=created_after,
        created_before=created_before,
        keywords=keywords,
        sort_by=sort_by
    )
    
    query = """
    query($batch_size: Int!, $searchQuery: String!, $afterCursor: String) {
        rateLimit {
            limit
            cost
            remaining
            resetAt
        }
        search(query: $searchQuery, type: REPOSITORY, first: $batch_size, after: $afterCursor) {
            repositoryCount
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                cursor
                node {
                    ... on Repository {
                        id
                        nameWithOwner
                        stargazerCount
                        createdAt
                        updatedAt
                    }
                }
            }
        }
    }
    """
    
    variables = {
        'batch_size': batch_size,
        'searchQuery': search_query,
        'afterCursor': after_cursor
    }
    
    response = send_crawl_request(query, variables)
    
    if response.status_code == 200:
        data = response.json()
        if 'errors' in data:
            print("GraphQL Errors:", data['errors'])
            return
            
        # Check rate limit
        print("*"*50 + "\nRate Limit Information\n" + "*"*50)
        rate_limit = data['data']['rateLimit']
        print("\nRate Limit Information:")
        print(f"Remaining: {rate_limit['remaining']}/{rate_limit['limit']}")
        print(f"Query Cost: {rate_limit['cost']}")
        print(f"Reset At: {rate_limit['resetAt']}")
        print("*"*50)
        
        # If we're close to rate limit, raise an exception
        if rate_limit['remaining'] < rate_limit['cost'] * 2:  # Keep buffer for 2 queries
            raise Exception(f"Rate limit nearly exceeded. Resets at {rate_limit['resetAt']}")
            
        search_data = data['data']['search']
        print(f"\nSearch Query: {search_query}")
        print(f"Total number of found repo: {search_data['repositoryCount']}")
        
        # Pagination information
        page_info = search_data['pageInfo']
        has_next_page = page_info['hasNextPage']
        end_cursor = page_info['endCursor']
        
        print(f"Showing {batch_size} repositories:")
        if has_next_page:
            print(f"More results available. Use cursor: {end_cursor}")
        return {
            'repositories': [edge['node'] for edge in search_data['edges']],
            'has_next_page': has_next_page,
            'end_cursor': end_cursor,
            'rate_limit': rate_limit
        }
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def db_write_batch(repo_data_list: List[Dict[Any, Any]], max_retries: int = 1) -> bool:
    """
    Write a batch of repository data to the database with retry mechanism.
    Only updates repositories if their star count has changed.
    
    Expected format for each dictionary:
    {
        "id": "ID",
        "nameWithOwner": "owner/repo",
        "stargazerCount": 100,
        "updatedAt": "2024-03-20T10:00:00Z"
    }
    """
    if not repo_data_list:
        return True

    for retry_count in range(max_retries):
        db = next(get_db())
        try:
            # Get all existing repositories with their current star counts
            existing_repos = {
                r.id: r for r in db.query(Repository).filter(
                    Repository.id.in_([r["id"] for r in repo_data_list])
                ).all()
            }
            
            current_time = datetime.utcnow()
            
            # Prepare updates and inserts
            to_update = []
            to_insert = []
            
            for repo_data in repo_data_list:
                repo = Repository(
                    id=repo_data["id"],
                    name=repo_data["nameWithOwner"],
                    star_count=repo_data["stargazerCount"],
                    updated_at=datetime.strptime(repo_data["updatedAt"], "%Y-%m-%dT%H:%M:%SZ"),
                    last_crawled_at=current_time
                )
                
                if repo.id in existing_repos:
                    # Only update if star count has changed
                    existing_repo = existing_repos[repo.id]
                    if existing_repo.star_count != repo.star_count:
                        to_update.append(repo)
                else:
                    to_insert.append(repo)
            
            # Bulk insert new repositories
            if to_insert:
                db.bulk_save_objects(to_insert)
            
            # Bulk update repositories with changed star counts
            if to_update:
                for repo in to_update:
                    db.merge(repo)
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error in db_write_batch: {str(e)}")
            db.rollback()
            if retry_count == max_retries - 1:
                return False
        finally:
            db.close()
    
    return False

def wait_for_rate_limit_reset(reset_at):
    """
    Waits until the rate limit resets
    """
    # Convert reset_at string to datetime
    reset_time = datetime.strptime(reset_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
    now = datetime.now(pytz.UTC)
    
    # Calculate wait time
    wait_seconds = (reset_time - now).total_seconds()
    if wait_seconds > 0:
        print(f"Rate limit reached. Waiting for {wait_seconds/60:.2f} minutes until {reset_at}")
        time.sleep(wait_seconds + 1)  # Add 1 second buffer

def get_month_date_range(year, month):
    """
    Returns the start and end date for a given year and month.
    Uses calendar to get the correct number of days in the month.
    """
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"
    return start_date, end_date

def get_next_date_range(year, month):
    """Helper function to get the next date range"""
    if month == 1:
        return year - 1, 12
    else:
        return year, month - 1

def crawl_worker(args, initial_year, initial_month, shared_counters, thread_key, max_retries=None):
    """Worker function for threaded crawling"""
    try:
        if max_retries is None:
            max_retries = settings.max_retries

        year = initial_year
        month = initial_month
        target_total = args.total_num_repo if args.total_num_repo else settings.total_num_repo
        
        while not check_total_repos(shared_counters, target_total):
            count_current_partition = 0
            after_cursor = None
            flag_no_more_page = False
            
            while not flag_no_more_page and count_current_partition < args.partition_threshold:
                if check_total_repos(shared_counters, target_total):
                    return
                    
                created_after, created_before = get_month_date_range(year, month)
                
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        with shared_counters['print_lock']:
                            print(f"Thread {thread_key} ({year}-{month:02d}) fetching from {created_after} to {created_before}")
                            print(f"Progress: {shared_counters['total'].get()}/{target_total} repositories")
                        
                        crawl_start_time = time.time()
                        
                        crawl_result = fetch_repositories(
                            batch_size=args.batch_size,
                            min_stars=args.min_stars,
                            language=args.language,
                            keywords=[args.keywords] if args.keywords else None,
                            sort_by=args.sort_by,
                            created_after=created_after,
                            created_before=created_before,
                            after_cursor=after_cursor
                        )
                        
                        crawl_time = time.time() - crawl_start_time
                        shared_counters['crawl_time'].increment(crawl_time)
                        shared_counters['crawl_ops'].increment()
                        
                        if not crawl_result:
                            raise Exception("Failed to fetch repositories")
                        
                        list_repo_data = crawl_result['repositories']
                        
                        write_start_time = time.time()
                        
                        if not db_write_batch(list_repo_data, max_retries=max_retries):
                            with shared_counters['print_lock']:
                                print("Failed to write batch to database, skipping this batch...")
                            continue
                        
                        write_time = time.time() - write_start_time
                        shared_counters['write_time'].increment(write_time)
                        shared_counters['write_ops'].increment()
                        
                        num_fetched = len(list_repo_data)
                        
                        # Update both counters
                        shared_counters['thread_counts'][thread_key].increment(num_fetched)
                        shared_counters['total'].increment(num_fetched)
                        
                        with shared_counters['print_lock']:
                            print(f"Thread {thread_key} ({year}-{month:02d}) fetched and saved {num_fetched} repositories")
                            print(f"Thread total: {shared_counters['thread_counts'][thread_key].get()}")
                            print(f"Crawl time: {crawl_time:.2f}s, Write time: {write_time:.2f}s")
                            
                            if shared_counters['crawl_ops'].get() > 0 and shared_counters['write_ops'].get() > 0:
                                avg_crawl = shared_counters['crawl_time'].get() / shared_counters['crawl_ops'].get()
                                avg_write = shared_counters['write_time'].get() / shared_counters['write_ops'].get()
                                print(f"Average times - Crawl: {avg_crawl:.2f}s, Write: {avg_write:.2f}s")
                        
                        count_current_partition += num_fetched
                        
                        if crawl_result['has_next_page']:
                            after_cursor = crawl_result['end_cursor']
                        else:
                            with shared_counters['print_lock']:
                                print(f"No more repositories for {year}-{month:02d}")
                            flag_no_more_page = True
                            break
                            
                    except Exception as e:
                        error_msg = str(e)
                        with shared_counters['print_lock']:
                            print(f"API Error occurred in thread {thread_key} ({year}-{month:02d}): {error_msg}")
                        
                        if "Rate limit nearly exceeded" in error_msg:
                            reset_at = error_msg.split("Resets at ")[-1]
                            wait_for_rate_limit_reset(reset_at)
                            continue
                        
                        retry_count += 1
                        if retry_count >= max_retries:
                            with shared_counters['print_lock']:
                                print(f"Max retries reached for thread {thread_key} ({year}-{month:02d}). Moving to next date range...")
                            flag_no_more_page = True
                            break
                        with shared_counters['print_lock']:
                            print(f"Retrying in 2 seconds... (Attempt {retry_count + 1}/{max_retries})")
                        time.sleep(2)
            
            # Move to next date range
            year, month = get_next_date_range(year, month)
            with shared_counters['print_lock']:
                print(f"Thread {thread_key} moving to new date range: {year}-{month:02d}")
                    
    except Exception as e:
        with shared_counters['print_lock']:
            print(f"Error in crawl_worker for thread {thread_key} ({year}-{month:02d}): {e}")

def crawl_pipeline(args, max_retries=None):
    try:
        if max_retries is None:
            max_retries = settings.max_retries
            
        # Set number of threads for parallel processing
        num_threads = args.num_threads
        target_total = args.total_num_repo if args.total_num_repo else settings.total_num_repo
        print(f"Starting multi-threaded crawl with {num_threads} threads (using GitHub token)")
        print(f"Target total repositories: {target_total}")

        # Initialize shared counters
        shared_counters = {
            'total': ThreadSafeCounter(0),
            'crawl_time': ThreadSafeCounter(0),
            'write_time': ThreadSafeCounter(0),
            'crawl_ops': ThreadSafeCounter(0),
            'write_ops': ThreadSafeCounter(0),
            'print_lock': Lock(),
            'thread_counts': {}  # Track per-thread counts
        }

        print("*"*80 + "\nGITHUB REPO Crawling...\n" + "*"*80)
        
        # Generate initial date ranges for threads
        date_ranges = []
        year = args.start_year
        month = args.start_month
        
        # Distribute initial date ranges across threads
        for _ in range(num_threads):
            date_ranges.append((year, month))
            year, month = get_next_date_range(year, month)
                
        print("\nStarting threads with initial date ranges:")
        for year, month in date_ranges:
            print(f"- {year}-{month:02d}")
        print(f"\nTarget total repositories: {target_total}\n")
        
        # Record start time for wall clock timing
        total_start_time = time.time()
        
        # Create thread pool and start crawling
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i, (year, month) in enumerate(date_ranges):
                thread_key = f"thread_{i}"
                shared_counters['thread_counts'][thread_key] = ThreadSafeCounter(0)
                futures.append(
                    executor.submit(
                        crawl_worker,
                        args,
                        year,
                        month,
                        shared_counters,
                        thread_key,
                        max_retries
                    )
                )
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        # Calculate total wall clock time
        total_wall_time = time.time() - total_start_time
        
        print("\n" + "*"*80 + "\nFinal Performance Statistics\n" + "*"*80)
        
        # Verify total count
        total_from_threads = sum(counter.get() for counter in shared_counters['thread_counts'].values())
        total_reported = shared_counters['total'].get()
        
        print("\nRepository Count Verification:")
        print(f"Total from thread counters: {total_from_threads}")
        print(f"Total from shared counter: {total_reported}")
        
        if total_from_threads != total_reported:
            print(f"WARNING: Count mismatch detected! Difference: {abs(total_from_threads - total_reported)}")
            print("\nPer-thread counts:")
            for thread_key, counter in shared_counters['thread_counts'].items():
                print(f"  {thread_key}: {counter.get()}")
        
        print(f"\nTotal repositories fetched: {total_from_threads}")
        
        if shared_counters['crawl_ops'].get() > 0 and shared_counters['write_ops'].get() > 0:
            total_crawl_time = shared_counters['crawl_time'].get()
            total_write_time = shared_counters['write_time'].get()
            total_crawl_ops = shared_counters['crawl_ops'].get()
            total_write_ops = shared_counters['write_ops'].get()
            
            print(f"\nOperation Statistics:")
            print(f"Total operations - Crawl: {total_crawl_ops}, Write: {total_write_ops}")
            print(f"Average time per operation:")
            print(f"  - Crawl: {(total_crawl_time/total_crawl_ops):.2f}s")
            print(f"  - Write: {(total_write_time/total_write_ops):.2f}s")
            print(f"\nParallel execution statistics ({num_threads} threads):")
            print(f"  - Total wall clock time: {total_wall_time:.2f}s")
            print(f"  - Cumulative crawl time: {total_crawl_time:.2f}s")
            print(f"  - Cumulative write time: {total_write_time:.2f}s")
            print(f"  - Cumulative processing time: {(total_crawl_time + total_write_time):.2f}s")
            print(f"  - Effective parallel speedup: {((total_crawl_time + total_write_time)/total_wall_time):.2f}x")
            print(f"  - Average processing rate: {(total_from_threads/total_wall_time):.2f} repos/second")
            
    except Exception as e:
        print(f"Error in crawl_pipeline: {e}")

def main():
    parser = argparse.ArgumentParser(description='GitHub Repository Crawler')
    parser.add_argument('--mode', choices=['pipeline', 'single'], default='pipeline',
                      help='Run mode: pipeline (full crawl) or single (one fetch)')
    parser.add_argument('--min-stars', type=int, default=settings.default_min_stars,
                      help='Minimum stars')
    parser.add_argument('--language', type=str, help='Programming language')
    parser.add_argument('--batch-size', type=int, default=settings.batch_size,
                      help='Batch size (max 100)')
    parser.add_argument('--keywords', type=str, help='Search keywords')
    parser.add_argument('--sort-by', choices=['stars', 'updated', 'created', 'forks', 'None'],
                      help='Sort results by')
    parser.add_argument('--created-after', type=str, help='Created after date (YYYY-MM-DD)')
    parser.add_argument('--created-before', type=str, help='Created before date (YYYY-MM-DD)')
    parser.add_argument('--start-year', type=int, default=settings.default_start_year,
                      help='Starting year for pipeline crawl')
    parser.add_argument('--start-month', type=int, default=settings.default_start_month,
                      help='Starting month for pipeline crawl')
    parser.add_argument('--partition-threshold', type=int, default=settings.default_partition_threshold,
                      help='Number of repos to fetch before changing date range (max 1000)')
    parser.add_argument('--total-num-repo', type=int, help='Override total number of repositories to fetch')
    parser.add_argument('--num-threads', type=int, default=2,
                      help='Number of threads to use for crawling (default: 2)')

    args = parser.parse_args()
    
    if args.mode == 'single':
        print("\nRunning single fetch_repositories() call...")
        result = fetch_repositories(
            batch_size=args.batch_size,
            min_stars=args.min_stars,
            language=args.language,
            keywords=[args.keywords] if args.keywords else None,
            sort_by=args.sort_by,
            created_after=args.created_after,
            created_before=args.created_before
        )
        if result:
            print(f"\nFetch completed successfully!")
            print(f"Fetched {len(result['repositories'])} repositories")
            print(f"Has next page: {result['has_next_page']}")
            if result['has_next_page']:
                print(f"Next cursor: {result['end_cursor']}")
    elif args.mode == 'pipeline':
        crawl_pipeline(args=args)

if __name__ == "__main__":
    main() 